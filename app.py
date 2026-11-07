"""
Localized Technical RAG Web Application - Streamlit Interface.
Inspired by Professor Glitch's document search agent.
Features:
- Split-screen layout: Interactive Chat on Left, Live Visual PDF Viewer on Right.
- Page-level citations with one-click jump & highlight.
- Visual PyMuPDF rendering + native PDF iframe viewer.
- Real-time ingestion manager with incremental indexing.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import streamlit as st
import streamlit.components.v1 as components

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import (
    DOCUMENTS_DIR,
    VECTOR_DB_DIR,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    get_api_key,
)
from src.pdf_viewer import (
    render_pdf_page_to_png,
    get_pdf_page_count,
    get_pdf_page_text,
    get_pdf_iframe_html,
)
from src.ingest import (
    run_ingestion,
    clear_vector_database,
    get_chroma_collection,
    load_manifest,
)
from src.retriever import DocumentRetriever
from src.agent import DocumentQAAgent, Citation, AgentResponse
from generate_sample_docs import generate_all_samples


# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Technical RAG - Doc Search Agent",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for split-screen styling and citation pills
st.markdown("""
<style>
    /* Compact top padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Header badge */
    .rag-badge {
        display: inline-block;
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    
    /* Citation button pill styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    
    /* PDF Viewer Box */
    .viewer-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 10px;
    }
    
    /* Chunk metadata badge */
    .meta-badge {
        background-color: #e2e8f0;
        color: #1e293b;
        font-size: 0.72rem;
        padding: 2px 8px;
        border-radius: 6px;
        font-family: monospace;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "active_doc" not in st.session_state:
    st.session_state["active_doc"] = None

if "active_doc_path" not in st.session_state:
    st.session_state["active_doc_path"] = None

if "active_page" not in st.session_state:
    st.session_state["active_page"] = 1

if "active_highlights" not in st.session_state:
    st.session_state["active_highlights"] = []

if "viewer_dpi" not in st.session_state:
    st.session_state["viewer_dpi"] = 150

if "api_key" not in st.session_state:
    st.session_state["api_key"] = get_api_key()

if "selected_model" not in st.session_state:
    st.session_state["selected_model"] = DEFAULT_GEMINI_MODEL

if "top_k" not in st.session_state:
    st.session_state["top_k"] = DEFAULT_TOP_K


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def get_available_pdfs() -> List[Path]:
    """List all available PDF files in documents directory."""
    if not DOCUMENTS_DIR.exists():
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(list(DOCUMENTS_DIR.rglob("*.pdf")), key=lambda p: p.name)


def set_active_document_and_page(doc_name: str, page_number: int, highlights: Optional[List[str]] = None):
    """Update active viewer document and page, triggering instant rerun."""
    pdfs = get_available_pdfs()
    matching = [p for p in pdfs if p.name.lower() == doc_name.lower()]
    if matching:
        target_path = matching[0]
        st.session_state["active_doc"] = target_path.name
        st.session_state["active_doc_path"] = str(target_path.resolve())
        st.session_state["active_page"] = max(1, page_number)
        if highlights:
            st.session_state["active_highlights"] = highlights
        st.rerun()


# Auto-select first document if none selected
available_pdfs = get_available_pdfs()
if not st.session_state["active_doc"] and available_pdfs:
    first_pdf = available_pdfs[0]
    st.session_state["active_doc"] = first_pdf.name
    st.session_state["active_doc_path"] = str(first_pdf.resolve())
    st.session_state["active_page"] = 1


# ---------------------------------------------------------
# Sidebar: Settings, Ingestion & Controls
# ---------------------------------------------------------
with st.sidebar:
    st.markdown('<span class="rag-badge">Control Center</span>', unsafe_allow_html=True)
    st.title("⚙️ RAG Configuration")

    # API Key Input
    api_key_input = st.text_input(
        "Gemini API Key",
        value=st.session_state["api_key"],
        type="password",
        placeholder="Enter AI Studio API Key...",
        help="Get your API key from https://aistudio.google.com/",
    )
    if api_key_input != st.session_state["api_key"]:
        st.session_state["api_key"] = api_key_input
        st.rerun()

    if st.session_state["api_key"]:
        st.success("API Key Active", icon="✅")
    else:
        st.warning("Please provide a Gemini API Key to enable embeddings and answers.", icon="⚠️")

    st.divider()

    # Model Selection
    model_choice = st.selectbox(
        "Gemini Model",
        options=[
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ],
        index=0,
        help="gemini-3.8-flash is the newest high-speed flagship model with enhanced reasoning and strict guardrail adherence.",
    )
    st.session_state["selected_model"] = model_choice

    # Top-K Retrieval
    top_k_val = st.slider(
        "Top-K Chunks to Retrieve",
        min_value=2,
        max_value=8,
        value=st.session_state["top_k"],
        help="Number of document context chunks fed into Gemini prompt.",
    )
    st.session_state["top_k"] = top_k_val

    st.divider()

    # Ingestion Status & Actions
    st.subheader("📚 Document Knowledge Base")
    try:
        col = get_chroma_collection()
        chunk_count = col.count()
    except Exception:
        chunk_count = 0

    manifest = load_manifest()
    indexed_files_count = len(manifest.get("files", {}))

    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Total PDFs", len(available_pdfs))
    with col_stat2:
        st.metric("Indexed Chunks", chunk_count)

    # Ingest button
    if st.button("🔄 Scan & Ingest PDFs", use_container_width=True, type="primary"):
        if not st.session_state["api_key"]:
            st.error("API Key is required to compute embeddings.")
        else:
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def update_progress(msg: str, pct: float):
                progress_bar.progress(min(1.0, max(0.0, pct)))
                status_text.text(msg)

            with st.spinner("Ingesting technical manuals..."):
                try:
                    result = run_ingestion(
                        api_key=st.session_state["api_key"],
                        force_reindex=False,
                        progress_callback=update_progress,
                    )
                    st.success(f"Ingestion Finished! Total DB Chunks: {result['total_chunks_in_db']}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Ingestion failed: {exc}")

    # Sample Documents generator
    if len(available_pdfs) == 0:
        st.info("No PDFs found in ./documents. Generate sample manuals to test immediately:")
        if st.button("✨ Generate Sample Technical Manuals", use_container_width=True):
            with st.spinner("Generating sample manuals..."):
                generate_all_samples()
                st.success("Sample manuals generated in ./documents!")
                st.rerun()

    # Clear DB Button
    if st.button("🗑️ Clear Vector Database", use_container_width=True):
        clear_vector_database()
        st.warning("Vector database and manifest cleared.")
        st.rerun()

    st.divider()

    # Available Documents List
    st.subheader("📂 Document Library")
    if available_pdfs:
        for p in available_pdfs:
            is_active = (p.name == st.session_state["active_doc"])
            label = f"{'🟢' if is_active else '📄'} {p.name}"
            if st.button(label, key=f"lib_doc_{p.name}", use_container_width=True):
                set_active_document_and_page(p.name, 1)
    else:
        st.caption("No PDFs found in ./documents directory.")


# ---------------------------------------------------------
# Main App Header
# ---------------------------------------------------------
st.markdown('<span class="rag-badge">Professor Glitch Architecture</span>', unsafe_allow_html=True)
st.title("Localized Technical Manual RAG")
st.caption("Factual, verified answers with real-time synchronized side-by-side visual PDF citations.")

# Split-Screen Layout: Left Column = Chat, Right Column = Live PDF Viewer
chat_col, viewer_col = st.columns([1, 1], gap="medium")


# =========================================================
# LEFT COLUMN: INTERACTIVE CHAT INTERFACE
# =========================================================
with chat_col:
    st.subheader("💬 Query Assistant")

    # Display chat message history
    for idx, msg in enumerate(st.session_state["messages"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Render citation action buttons and retrieved context
            if msg["role"] == "assistant":
                citations: List[Citation] = msg.get("citations", [])
                context_chunks = msg.get("context_chunks", [])
                is_proven = msg.get("proven", True)

                if is_proven and citations:
                    st.markdown("**Visual Citations (Click to inspect source page):**")
                    cols = st.columns(min(len(citations), 3))
                    for c_idx, cite in enumerate(citations):
                        col_target = cols[c_idx % len(cols)]
                        with col_target:
                            button_label = f"📄 {cite.file_name} (p. {cite.page_number})"
                            if st.button(button_label, key=f"cite_action_{idx}_{c_idx}"):
                                set_active_document_and_page(
                                    doc_name=cite.file_name,
                                    page_number=cite.page_number,
                                    highlights=[cite.snippet] if cite.snippet else None,
                                )

                if not is_proven:
                    st.warning("⚠️ Unproven by available documents: Gemini strictly refrained from hallucinating.")

                if context_chunks:
                    with st.expander(f"🔍 Retrieved Evidence ({len(context_chunks)} chunks)"):
                        for c in context_chunks:
                            st.markdown(
                                f"<span class='meta-badge'>{c['file_name']}</span>"
                                f"<span class='meta-badge'>Page {c['page_number']}</span>"
                                f"<span class='meta-badge'>Similarity: {int(c['similarity']*100)}%</span>",
                                unsafe_allow_html=True,
                            )
                            st.text(c["text"][:300] + ("..." if len(c["text"]) > 300 else ""))
                            st.divider()

    # Chat Input Box
    user_query = st.chat_input("Ask a question about the technical manuals (e.g., 'What is Error E-405 on the P200 robot?')")

    if user_query:
        # Check API Key
        if not st.session_state["api_key"]:
            st.error("Please enter a Gemini API Key in the left sidebar to proceed.")
        elif chunk_count == 0:
            st.error("No documents indexed yet! Please click 'Scan & Ingest PDFs' in the sidebar first.")
        else:
            # Append user message
            st.session_state["messages"].append({
                "role": "user",
                "content": user_query,
            })

            # Execute RAG Agent
            with st.spinner("Retrieving evidence & synthesizing response..."):
                try:
                    retriever = DocumentRetriever(
                        api_key=st.session_state["api_key"],
                        db_path=VECTOR_DB_DIR,
                        embedding_model=DEFAULT_EMBEDDING_MODEL,
                    )
                    agent = DocumentQAAgent(
                        api_key=st.session_state["api_key"],
                        model_name=st.session_state["selected_model"],
                        retriever=retriever,
                    )

                    response: AgentResponse = agent.answer_query(
                        query=user_query,
                        top_k=st.session_state["top_k"],
                    )

                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": response.answer,
                        "citations": response.citations,
                        "context_chunks": response.context_chunks,
                        "proven": response.proven,
                    })

                    # Auto-focus the first cited page on the right viewer
                    if response.proven and response.citations:
                        first_cite = response.citations[0]
                        matching = [p for p in available_pdfs if p.name.lower() == first_cite.file_name.lower()]
                        if matching:
                            st.session_state["active_doc"] = matching[0].name
                            st.session_state["active_doc_path"] = str(matching[0].resolve())
                            st.session_state["active_page"] = first_cite.page_number
                            st.session_state["active_highlights"] = [first_cite.file_name.replace(".pdf", "")]

                    st.rerun()

                except Exception as exc:
                    st.error(f"Error querying documents: {exc}")


# =========================================================
# RIGHT COLUMN: LIVE SYNCHRONIZED PDF VIEWER
# =========================================================
with viewer_col:
    st.subheader("👁️ Live Document Viewer")

    active_doc = st.session_state.get("active_doc")
    active_path = st.session_state.get("active_doc_path")
    active_page = st.session_state.get("active_page", 1)

    if not active_doc or not active_path or not Path(active_path).is_file():
        st.info("No active document selected. Select a document from the sidebar or click a citation in chat.")
    else:
        total_pages = get_pdf_page_count(active_path)
        if total_pages == 0:
            st.error(f"Could not load PDF: {active_doc}")
        else:
            # Bound page number
            active_page = max(1, min(active_page, total_pages))
            st.session_state["active_page"] = active_page

            # Viewer Header & Navigation Bar
            nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([2, 1, 1, 1.5, 1.5])

            with nav_col1:
                st.markdown(f"**📄 {active_doc}**")

            with nav_col2:
                if st.button("◀ Prev", disabled=(active_page <= 1), use_container_width=True):
                    st.session_state["active_page"] = active_page - 1
                    st.rerun()

            with nav_col3:
                if st.button("Next ▶", disabled=(active_page >= total_pages), use_container_width=True):
                    st.session_state["active_page"] = active_page + 1
                    st.rerun()

            with nav_col4:
                page_jump = st.number_input(
                    "Page",
                    min_value=1,
                    max_value=total_pages,
                    value=active_page,
                    step=1,
                    label_visibility="collapsed",
                )
                if page_jump != active_page:
                    st.session_state["active_page"] = int(page_jump)
                    st.rerun()

            with nav_col5:
                dpi_choice = st.selectbox(
                    "Zoom",
                    options=[100, 150, 200],
                    index=1,
                    label_visibility="collapsed",
                    help="Render DPI for visual preview",
                )
                st.session_state["viewer_dpi"] = dpi_choice

            st.caption(f"Displaying Page **{active_page}** of **{total_pages}**")

            # Tabs: Visual Render (PyMuPDF) vs Native PDF Embed vs Raw Page Text
            tab_render, tab_embed, tab_text = st.tabs([
                "🖼️ Rendered Page Preview",
                "📄 Native PDF Viewer",
                "📝 Extracted Page Text",
            ])

            with tab_render:
                highlights = st.session_state.get("active_highlights", [])
                png_bytes = render_pdf_page_to_png(
                    pdf_path=active_path,
                    page_number=active_page,
                    dpi=st.session_state["viewer_dpi"],
                    highlight_terms=highlights,
                )
                if png_bytes:
                    st.image(
                        png_bytes,
                        caption=f"{active_doc} - Page {active_page}",
                        use_container_width=True,
                    )
                else:
                    st.error("Failed to render page image.")

            with tab_embed:
                iframe_code = get_pdf_iframe_html(
                    pdf_path=active_path,
                    page_number=active_page,
                    height=750,
                )
                components.html(iframe_code, height=760)

            with tab_text:
                page_text = get_pdf_page_text(active_path, active_page)
                if page_text:
                    st.text_area(
                        f"Text content of Page {active_page}",
                        value=page_text,
                        height=600,
                        disabled=True,
                    )
                else:
                    st.caption("No extractable text on this page.")
