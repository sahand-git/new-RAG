"""
Data Ingestion and Parsing Engine for Localized Technical Manuals RAG.
Recursively parses PDF documents, performs token-aware chunking with page metadata preservation,
generates Gemini embeddings, and persists vectors into ChromaDB.
"""

import os
import sys
import json
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
import pymupdf
import chromadb
from google import genai

from src.config import (
    DOCUMENTS_DIR,
    VECTOR_DB_DIR,
    CHROMA_COLLECTION_NAME,
    DEFAULT_EMBEDDING_MODEL,
    CHUNK_SIZE_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    ESTIMATED_CHARS_PER_TOKEN,
    get_api_key,
    create_genai_client,
)


def compute_file_hash(file_path: Path) -> str:
    """Compute MD5 checksum of a file to detect changes."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def split_text_into_chunks(
    text: str,
    target_tokens: int = CHUNK_SIZE_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    chars_per_token: int = ESTIMATED_CHARS_PER_TOKEN,
) -> List[str]:
    """
    Split text into chunks aiming for target_tokens with overlap_tokens overlap.
    Preserves paragraph and sentence boundaries where possible.
    """
    text = text.strip()
    if not text:
        return []

    target_chars = target_tokens * chars_per_token
    overlap_chars = overlap_tokens * chars_per_token

    if len(text) <= target_chars:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + target_chars, text_len)

        # If not at the very end of text, seek a natural boundary
        if end < text_len:
            # Look backwards up to 200 chars for sentence or paragraph end
            search_window = text[max(start, end - 200):end]
            match = re.search(r"(\.\s+|\n\n|\n|\!\s+|\?\s+)[^\.\n\!\?]*$", search_window)
            if match:
                boundary_offset = len(search_window) - match.start(1) - len(match.group(1))
                end = end - boundary_offset
            else:
                # Fall back to word boundary
                space_pos = text.rfind(" ", max(start, end - 100), end)
                if space_pos > start:
                    end = space_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        # Advance start with overlap
        step = max(100, (end - start) - overlap_chars)
        start += step

    return chunks


def extract_chunks_from_pdf(
    pdf_path: Path,
    target_tokens: int = CHUNK_SIZE_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> List[Dict[str, Any]]:
    """
    Parse a single PDF file page by page using PyMuPDF.
    Returns a list of chunk dictionaries with strict metadata:
    { file_name, file_path, page_number, chunk_id, total_pages, text }
    """
    chunks_data = []
    doc_name = pdf_path.name
    doc_str_path = str(pdf_path.resolve())

    try:
        with pymupdf.open(doc_str_path) as doc:
            total_pages = len(doc)
            file_hash = compute_file_hash(pdf_path)

            for page_idx in range(total_pages):
                page_num = page_idx + 1  # 1-indexed page
                page = doc[page_idx]
                page_text = page.get_text("text")

                if not page_text or not page_text.strip():
                    continue

                page_chunks = split_text_into_chunks(
                    text=page_text,
                    target_tokens=target_tokens,
                    overlap_tokens=overlap_tokens,
                )

                for chunk_idx, chunk_text in enumerate(page_chunks):
                    chunk_id = f"{pdf_path.stem}_p{page_num}_c{chunk_idx+1}_{file_hash[:6]}"
                    chunks_data.append({
                        "id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            "file_name": doc_name,
                            "file_path": doc_str_path,
                            "page_number": int(page_num),
                            "total_pages": int(total_pages),
                            "chunk_id": chunk_id,
                            "chunk_index": int(chunk_idx),
                            "file_hash": file_hash,
                        }
                    })
    except Exception as exc:
        print(f"[ingest] Error reading {pdf_path}: {exc}", file=sys.stderr)

    return chunks_data


def get_chroma_collection(db_path: Path = VECTOR_DB_DIR) -> chromadb.Collection:
    """Initialize or load the persistent ChromaDB collection."""
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )


def generate_gemini_embeddings(
    texts: List[str],
    api_key: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 50,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using the official google-genai SDK.
    Configured with v1beta endpoint to support text-embedding-004.
    """
    if not api_key:
        raise ValueError("Gemini API key is required to generate embeddings.")

    client = create_genai_client(api_key=api_key)
    all_embeddings = []

    # Model candidates to try if specified model returns 404
    candidate_models = [model]
    if not model.startswith("models/"):
        candidate_models.append(f"models/{model}")
    else:
        candidate_models.append(model.replace("models/", ""))
    if "text-embedding-004" not in candidate_models:
        candidate_models.append("text-embedding-004")
    candidate_models.append("embedding-001")

    working_model = None

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embedded = False

        models_to_attempt = [working_model] if working_model else candidate_models

        for candidate in models_to_attempt:
            if not candidate:
                continue
            try:
                response = client.models.embed_content(
                    model=candidate,
                    contents=batch,
                )
                batch_vectors = [emb.values for emb in response.embeddings]
                all_embeddings.extend(batch_vectors)
                working_model = candidate
                embedded = True
                break
            except Exception as batch_exc:
                err_msg = str(batch_exc)
                if "404" in err_msg or "not found" in err_msg.lower():
                    continue
                else:
                    # Retry item by item if batch fails
                    try:
                        for single_text in batch:
                            s_resp = client.models.embed_content(
                                model=candidate,
                                contents=single_text,
                            )
                            if s_resp.embeddings:
                                all_embeddings.append(s_resp.embeddings[0].values)
                        working_model = candidate
                        embedded = True
                        break
                    except Exception:
                        continue

        if not embedded:
            raise RuntimeError(
                f"Failed to generate embeddings. Tried models: {candidate_models}. "
                "Please verify your Gemini API key has access to the Gemini Embeddings API."
            )

    return all_embeddings


def load_manifest(db_path: Path = VECTOR_DB_DIR) -> Dict[str, Any]:
    """Load the ingestion manifest tracking indexed files and hashes."""
    manifest_file = db_path / "manifest.json"
    if manifest_file.is_file():
        try:
            return json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}}


def save_manifest(manifest_data: Dict[str, Any], db_path: Path = VECTOR_DB_DIR) -> None:
    """Save the ingestion manifest."""
    manifest_file = db_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")


def run_ingestion(
    documents_dir: Path = DOCUMENTS_DIR,
    vector_db_dir: Path = VECTOR_DB_DIR,
    api_key: Optional[str] = None,
    force_reindex: bool = False,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Dict[str, Any]:
    """
    Main ingestion routine:
    1. Scan ./documents recursively for all .pdf files.
    2. Compare file hashes with manifest.
    3. Extract text chunks with full page metadata.
    4. Compute embeddings using Google GenAI SDK.
    5. Upsert to ChromaDB vector store.
    """
    key = api_key or get_api_key()
    if not key:
        raise ValueError("Gemini API key is not configured. Set GEMINI_API_KEY in .env or pass it directly.")

    documents_dir = Path(documents_dir).resolve()
    vector_db_dir = Path(vector_db_dir).resolve()

    if not documents_dir.exists():
        documents_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(documents_dir.rglob("*.pdf"))
    collection = get_chroma_collection(vector_db_dir)
    manifest = load_manifest(vector_db_dir)
    indexed_files = manifest.setdefault("files", {})

    total_files = len(pdf_files)
    if total_files == 0:
        if progress_callback:
            progress_callback("No PDF documents found in documents directory.", 1.0)
        return {
            "status": "empty",
            "message": f"No PDF files found in {documents_dir}",
            "processed_files": 0,
            "total_chunks": collection.count(),
        }

    processed_count = 0
    skipped_count = 0
    new_chunks_count = 0

    if progress_callback:
        progress_callback(f"Discovered {total_files} PDF manuals. Checking index...", 0.05)

    for idx, pdf_path in enumerate(pdf_files):
        file_name = pdf_path.name
        current_hash = compute_file_hash(pdf_path)
        last_info = indexed_files.get(file_name)

        # Check if already indexed and unchanged
        if not force_reindex and last_info and last_info.get("hash") == current_hash:
            skipped_count += 1
            if progress_callback:
                progress_callback(f"Skipping unchanged document: {file_name}", (idx + 1) / total_files)
            continue

        if progress_callback:
            progress_callback(f"Parsing pages & chunking: {file_name}", (idx + 0.3) / total_files)

        # If re-indexing an existing file with changes, remove previous chunks
        if last_info:
            try:
                collection.delete(where={"file_name": file_name})
            except Exception:
                pass

        # Extract chunks with page-level metadata
        chunks = extract_chunks_from_pdf(pdf_path)
        if not chunks:
            if progress_callback:
                progress_callback(f"No readable text found in {file_name}", (idx + 1) / total_files)
            continue

        if progress_callback:
            progress_callback(f"Generating Gemini embeddings for {file_name} ({len(chunks)} chunks)...", (idx + 0.6) / total_files)

        texts = [c["text"] for c in chunks]
        embeddings = generate_gemini_embeddings(texts=texts, api_key=key)

        # Upsert into ChromaDB
        ids = [c["id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        # Update manifest
        indexed_files[file_name] = {
            "path": str(pdf_path.resolve()),
            "hash": current_hash,
            "chunks": len(chunks),
            "pages": chunks[0]["metadata"]["total_pages"] if chunks else 0,
        }
        processed_count += 1
        new_chunks_count += len(chunks)

        if progress_callback:
            progress_callback(f"Indexed {file_name} successfully ({len(chunks)} chunks).", (idx + 1) / total_files)

    save_manifest(manifest, vector_db_dir)

    result = {
        "status": "success",
        "total_files": total_files,
        "processed_files": processed_count,
        "skipped_files": skipped_count,
        "new_chunks_indexed": new_chunks_count,
        "total_chunks_in_db": collection.count(),
    }

    if progress_callback:
        progress_callback(
            f"Ingestion complete: {processed_count} files processed, {skipped_count} skipped, {collection.count()} total chunks in DB.",
            1.0
        )

    return result


def clear_vector_database(vector_db_dir: Path = VECTOR_DB_DIR) -> None:
    """Clear the persistent ChromaDB collection and reset manifest."""
    try:
        client = chromadb.PersistentClient(path=str(vector_db_dir))
        client.delete_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        pass

    manifest_file = vector_db_dir / "manifest.json"
    if manifest_file.is_file():
        manifest_file.unlink(missing_ok=True)


if __name__ == "__main__":
    print(f"Starting Ingestion Engine...")
    print(f"Documents directory: {DOCUMENTS_DIR}")
    print(f"Vector DB directory: {VECTOR_DB_DIR}")

    api_key = get_api_key()
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        print("Please set GEMINI_API_KEY in your .env file or environment.", file=sys.stderr)
        sys.exit(1)

    def print_progress(msg: str, pct: float):
        print(f"[{int(pct * 100)}%] {msg}")

    try:
        res = run_ingestion(progress_callback=print_progress)
        print("\nIngestion Summary:")
        for k, v in res.items():
            print(f" - {k}: {v}")
    except Exception as e:
        print(f"Ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)
