"""
Search & Retrieval Pipeline.
Performs semantic vector search against local ChromaDB index using Gemini embeddings,
retrieving the top-K context chunks enriched with document name and page number metadata.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from google import genai
import chromadb

from src.config import (
    VECTOR_DB_DIR,
    CHROMA_COLLECTION_NAME,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    get_api_key,
    create_genai_client,
)
from src.ingest import get_chroma_collection


class DocumentRetriever:
    """Handles query embedding and similarity retrieval from ChromaDB."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        db_path: Path = VECTOR_DB_DIR,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            raise ValueError("Retriever requires a valid Gemini API key.")

        self.db_path = Path(db_path)
        self.embedding_model = embedding_model
        self.client = create_genai_client(api_key=self.api_key)
        self.collection = get_chroma_collection(self.db_path)

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding vector for search query with model fallback."""
        candidates = [self.embedding_model]
        if not self.embedding_model.startswith("models/"):
            candidates.append(f"models/{self.embedding_model}")
        else:
            candidates.append(self.embedding_model.replace("models/", ""))
        candidates.append("text-embedding-004")
        candidates.append("embedding-001")

        for model_name in candidates:
            try:
                resp = self.client.models.embed_content(
                    model=model_name,
                    contents=query.strip(),
                )
                if resp.embeddings:
                    self.embedding_model = model_name
                    return resp.embeddings[0].values
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    continue
                raise e

        raise RuntimeError(f"Failed to generate embedding for query: {query}")

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        filter_document: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search vector database for top-K most similar chunks to query.
        Optionally filter by a specific document name.
        """
        if self.collection.count() == 0:
            return []

        query_vector = self.embed_query(query)
        where_clause = {"file_name": filter_document} if filter_document else None

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, self.collection.count()),
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        formatted_chunks = []
        if not results or not results.get("ids") or len(results["ids"][0]) == 0:
            return []

        ids = results["ids"][0]
        docs = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for chunk_id, doc_text, meta, dist in zip(ids, docs, metadatas, distances):
            similarity_score = max(0.0, min(1.0, 1.0 - dist))
            formatted_chunks.append({
                "chunk_id": chunk_id,
                "text": doc_text,
                "file_name": meta.get("file_name", "Unknown"),
                "file_path": meta.get("file_path", ""),
                "page_number": int(meta.get("page_number", 1)),
                "total_pages": int(meta.get("total_pages", 1)),
                "similarity": round(similarity_score, 4),
                "distance": round(dist, 4),
            })

        return formatted_chunks

    @staticmethod
    def format_context_for_prompt(chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks into a clean, strongly-demarcated context block
        for Gemini system prompt ingestion.
        """
        if not chunks:
            return "No relevant documents found."

        context_lines = []
        for i, chunk in enumerate(chunks, 1):
            file_name = chunk["file_name"]
            page_num = chunk["page_number"]
            chunk_id = chunk["chunk_id"]
            text = chunk["text"]

            header = f"--- CONTEXT CHUNK {i} [Source: {file_name}, Page: {page_num}] ---"
            context_lines.append(header)
            context_lines.append(text)
            context_lines.append("-" * len(header))
            context_lines.append("")

        return "\n".join(context_lines)
