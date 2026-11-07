from unittest.mock import MagicMock
from pathlib import Path
from src.retriever import DocumentRetriever
from src.config import CHROMA_COLLECTION_NAME
import chromadb


def test_retriever_format_context():
    sample_chunks = [
        {
            "chunk_id": "test_c1",
            "file_name": "Manual_P200.pdf",
            "file_path": "/docs/Manual_P200.pdf",
            "page_number": 4,
            "total_pages": 5,
            "similarity": 0.92,
            "distance": 0.08,
            "text": "Error E-405 indicates a resolver communication timeout."
        }
    ]
    formatted = DocumentRetriever.format_context_for_prompt(sample_chunks)
    assert "Manual_P200.pdf" in formatted
    assert "Page: 4" in formatted
    assert "Error E-405" in formatted


def test_retriever_query_mock(tmp_path: Path):
    # Initialize Chroma in temporary path
    client = chromadb.PersistentClient(path=str(tmp_path))
    col = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    # Upsert test item
    col.upsert(
        ids=["chunk_1"],
        documents=["Test document content about hydraulic pressure."],
        metadatas=[{"file_name": "Hydraulics.pdf", "file_path": "/path/Hydraulics.pdf", "page_number": 12, "total_pages": 30, "chunk_id": "chunk_1"}],
        embeddings=[[0.05] * 768],
    )

    # Mock DocumentRetriever
    retriever = DocumentRetriever.__new__(DocumentRetriever)
    retriever.collection = col
    retriever.embed_query = MagicMock(return_value=[0.05] * 768)

    results = retriever.retrieve(query="hydraulic pressure", top_k=1)
    assert len(results) == 1
    assert results[0]["file_name"] == "Hydraulics.pdf"
    assert results[0]["page_number"] == 12
    assert "hydraulic pressure" in results[0]["text"]
