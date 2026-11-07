from src.ingest import split_text_into_chunks, extract_chunks_from_pdf
from src.config import DOCUMENTS_DIR


def test_split_text_into_chunks_basic():
    short_text = "This is a short paragraph. It should fit into a single chunk."
    chunks = split_text_into_chunks(short_text, target_tokens=100, overlap_tokens=10)
    assert len(chunks) == 1
    assert chunks[0] == short_text


def test_split_text_into_chunks_long():
    # Generate repeated sentences to trigger multi-chunk splitting
    sentence = "The turbine bearing operates at 65 degrees Celsius under normal loads. "
    long_text = sentence * 60  # ~4300 chars, ~1000+ tokens

    chunks = split_text_into_chunks(
        long_text,
        target_tokens=100,  # ~400 chars
        overlap_tokens=20,  # ~80 chars
    )
    assert len(chunks) > 2
    # Ensure every chunk is non-empty
    for c in chunks:
        assert len(c.strip()) > 0
        assert "turbine bearing" in c


def test_extract_chunks_from_pdf():
    pdf_path = DOCUMENTS_DIR / "Manual_P200_Robotics.pdf"
    chunks = extract_chunks_from_pdf(pdf_path)

    assert len(chunks) >= 5, "Should have at least 5 chunks for a 5-page manual"

    # Check metadata integrity
    page_numbers_seen = set()
    for chunk in chunks:
        meta = chunk["metadata"]
        assert "file_name" in meta
        assert meta["file_name"] == "Manual_P200_Robotics.pdf"
        assert "page_number" in meta
        assert 1 <= meta["page_number"] <= 5
        page_numbers_seen.add(meta["page_number"])
        assert "chunk_id" in meta
        assert "total_pages" in meta
        assert meta["total_pages"] == 5

    # All 5 pages should have generated chunks
    assert len(page_numbers_seen) == 5


if __name__ == "__main__":
    test_split_text_into_chunks_basic()
    test_split_text_into_chunks_long()
    test_extract_chunks_from_pdf()
    print("All chunking tests passed!")
