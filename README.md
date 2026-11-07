# Localized Technical Manual RAG Web Application
> **Inspired by Professor Glitch's Document Search Agent**  
> A high-speed, factually strict technical manual lookup engine powered by **Google Gemini** (via the official `google-genai` SDK), **ChromaDB**, **PyMuPDF**, and **Streamlit**.

---

## 🌟 Overview

Technical documents, industrial manuals, and aerospace standard operating procedures require **100% factual accuracy**. Standard RAG pipelines frequently hallucinate or provide vague answers without exact citations.

This application provides:
1. **Zero-Hallucination Guardrails**: Strict Gemini system instructions that only answer from retrieved context chunks. If the answer is not present, it responds strictly with: `"I cannot prove this from the available documents."`
2. **Side-by-Side Visual Citations**: When Gemini cites a manual (e.g., `Manual_P200_Robotics.pdf, Page 4`), clicking the citation immediately loads the document in the right-hand viewer pane and jumps directly to that exact page.
3. **Dual Visual Inspection Engine**: High-resolution PyMuPDF page rendering with term highlights plus a native browser PDF viewer tab.
4. **Incremental Ingestion**: File-hash based indexing that avoids re-embedding unchanged documents.

---

## 📐 Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      LOCAL DOCUMENT STORE                     │
│                        (./documents/*.pdf)                    │
└───────────────────────────────┬───────────────────────────────┘
                                │
                   (1) PyMuPDF Page-by-Page Parser
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                      TOKEN-AWARE CHUNKER                      │
│     500-token chunks with 50-token overlap + page metadata    │
│       { file_name, file_path, page_number, chunk_id }        │
└───────────────────────────────┬───────────────────────────────┘
                                │
             (2) Gemini Embeddings (text-embedding-004)
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    CHROMADB VECTOR STORE                      │
│                    (./vector_db - Cosine HNSW)                │
└───────────────────────────────┬───────────────────────────────┘
                                │
             (3) Top-K Similarity Search on User Query
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    GEMINI STRICT AGENT                        │
│          Model: gemini-2.5-flash (Zero Temperature)           │
│   System Prompt: Answer ONLY from context or declare unproven │
└───────────────────────────────┬───────────────────────────────┘
                                │
                (4) Answer + Page Citation Triggers
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                  STREAMLIT SPLIT-SCREEN UI                    │
│   [Left Column] Interactive Chat  |  [Right Column] Live PDF  │
│    - Factual answer               |   - Page-jumping preview  │
│    - Clickable citation pills     |   - High-res PyMuPDF view │
│    - Retrieved chunks inspector   |   - Native PDF iframe     │
└───────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Rag uild/
├── app.py                      # Main Streamlit split-screen application
├── generate_sample_docs.py     # Generator for realistic technical manuals (5 pages each)
├── requirements.txt            # Project dependencies
├── .env.example                # Template for environment variables
├── documents/                  # Local directory for technical manual PDFs
│   ├── Manual_P200_Robotics.pdf
│   └── Turbine_Generator_T900_Guide.pdf
├── vector_db/                  # Persistent ChromaDB vector index & manifest
├── src/
│   ├── __init__.py
│   ├── config.py               # Paths, model names, and guardrail prompts
│   ├── ingest.py               # PDF parser, chunker, Gemini embedder & indexer
│   ├── retriever.py            # Similarity search & context payload formatter
│   ├── agent.py                # Gemini QA Agent with guardrails & citation parser
│   └── pdf_viewer.py           # PyMuPDF renderer (Page to PNG & PDF iframe)
└── tests/
    ├── test_pdf_viewer.py      # Tests for PDF rendering and page extraction
    ├── test_chunking.py        # Tests for 500/50 token chunking & metadata
    └── test_citations.py       # Tests for citation regex and guardrail checks
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: 3.10, 3.11, or 3.12
- **Gemini API Key**: Obtain a free API key from [Google AI Studio](https://aistudio.google.com/).

### 2. Installation
Clone or navigate to the project directory:
```bash
cd "Rag uild"
```

Create a virtual environment and install dependencies:
```bash
# Using standard venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Or using uv (recommended for ultra-fast installs)
uv venv
uv pip install -r requirements.txt
```

### 3. Configure API Key
Copy `.env.example` to `.env` and insert your Gemini API Key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-004
```
*(Alternatively, you can paste your API key directly into the Streamlit sidebar at runtime).*

### 4. Generate Sample Technical Manuals (Optional)
If you do not have technical manuals on hand, generate two multi-page test manuals:
```bash
python generate_sample_docs.py
```
This generates:
- `Manual_P200_Robotics.pdf` (5 pages: Specs, Safety, Axis Zeroing, Fault Codes, Maintenance)
- `Turbine_Generator_T900_Guide.pdf` (5 pages: Thermodynamics, Fuel System, Bearing Lubrication, Rotor Coupling, Emergency Trip Limits)

### 5. Ingest Documents into Vector DB
You can ingest documents via CLI or directly through the UI:
```bash
python -m src.ingest
```

### 6. Launch the Streamlit Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 💡 How to Use the Application

1. **Verify Connection**:
   - Check the sidebar to ensure your Gemini API key is active.
   - Click **"Scan & Ingest PDFs"** to index all files in `./documents`.
2. **Ask Technical Questions**:
   - *"What is Error E-405 on the P200 robot and how do I fix it?"*
   - *"What is the required preload torque for the T900 turbine rotor coupling bolts?"*
   - *"What lubricant is required for the P200 harmonic drive gears?"*
   - *"What is the warranty period for the solar inverter?"* *(Returns: `"I cannot prove this from the available documents."`)*
3. **Click Citations for Visual Proof**:
   - Each answer presents citation buttons (e.g., `📄 Manual_P200_Robotics.pdf (p. 4)`).
   - Clicking any citation automatically updates the live viewer on the right and jumps straight to that exact page!
4. **Switch Viewer Tabs**:
   - **Rendered Page Preview**: High-resolution image of the page with citation terms highlighted.
   - **Native PDF Viewer**: Embedded interactive browser PDF viewer.
   - **Extracted Page Text**: Raw text content with instant search inspection.

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:
```bash
pytest tests/ -v
```

---

## 🛡️ Guardrails & Safety Design

| Guardrail Feature | Implementation Detail |
|---|---|
| **Zero Temperature** | `temperature=0.0` prevents creative interpolation or stylistic drift. |
| **Grounding Mandate** | System prompt instructs Gemini to use **ONLY** the provided excerpts. |
| **Fallback Refusal** | If facts are missing from retrieved chunks, Gemini outputs: `"I cannot prove this from the available documents."` |
| **Page-Level Anchor** | Every chunk carries `{ file_name, file_path, page_number }` to ensure provenance. |
