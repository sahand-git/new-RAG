from src.agent import DocumentQAAgent, Citation


def test_citation_extraction_bracket():
    agent = DocumentQAAgent.__new__(DocumentQAAgent)
    sample_text = (
        "The P200 robot has a payload capacity of 25.0 kg [Manual_P200_Robotics.pdf, Page 1]. "
        "In addition, the E-Stop loop complies with ISO 10218-1 [Manual_P200_Robotics.pdf, Page 2]."
    )
    retrieved_chunks = [
        {"file_name": "Manual_P200_Robotics.pdf", "file_path": "/path/Manual_P200_Robotics.pdf", "page_number": 1, "text": "payload"},
        {"file_name": "Manual_P200_Robotics.pdf", "file_path": "/path/Manual_P200_Robotics.pdf", "page_number": 2, "text": "safety"},
    ]

    citations = agent.extract_citations(sample_text, retrieved_chunks)
    assert len(citations) == 2
    pages = {c.page_number for c in citations}
    assert pages == {1, 2}
    assert all(c.file_name == "Manual_P200_Robotics.pdf" for c in citations)


def test_citation_extraction_freeform():
    agent = DocumentQAAgent.__new__(DocumentQAAgent)
    sample_text = (
        "According to Turbine_Generator_T900_Guide.pdf, Page 4, the rotor coupling bolts "
        "must be torqued to 1,450 Nm."
    )
    retrieved_chunks = [
        {"file_name": "Turbine_Generator_T900_Guide.pdf", "file_path": "/path/Turbine_Generator_T900_Guide.pdf", "page_number": 4, "text": "torqued"},
    ]

    citations = agent.extract_citations(sample_text, retrieved_chunks)
    assert len(citations) == 1
    assert citations[0].file_name == "Turbine_Generator_T900_Guide.pdf"
    assert citations[0].page_number == 4


def test_unproven_citations():
    agent = DocumentQAAgent.__new__(DocumentQAAgent)
    unproven_text = "I cannot prove this from the available documents."
    citations = agent.extract_citations(unproven_text, [])
    assert len(citations) == 0


if __name__ == "__main__":
    test_citation_extraction_bracket()
    test_citation_extraction_freeform()
    test_unproven_citations()
    print("All citation tests passed!")
