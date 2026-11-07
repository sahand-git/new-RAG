import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(BASE_DIR / "documents"))).resolve()
VECTOR_DB_DIR = Path(os.getenv("CHROMA_DB_DIR", str(BASE_DIR / "vector_db"))).resolve()

# Gemini Models
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# Chunking Parameters (500 tokens ~ 2000 characters, 50 tokens ~ 200 characters)
CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "500"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))
ESTIMATED_CHARS_PER_TOKEN = 4

CHUNK_SIZE_CHARS = CHUNK_SIZE_TOKENS * ESTIMATED_CHARS_PER_TOKEN
CHUNK_OVERLAP_CHARS = CHUNK_OVERLAP_TOKENS * ESTIMATED_CHARS_PER_TOKEN

# Retrieval settings
DEFAULT_TOP_K = 4
CHROMA_COLLECTION_NAME = "technical_documents"

# Strict System Prompt
SYSTEM_PROMPT = (
    "You are a strict technical document assistant. "
    "Answer the user question based ONLY on the provided context chunks. "
    "Include explicit page references in your output (e.g., [Document Name, Page X]). "
    "If the question cannot be definitively answered from the context, respond strictly with: "
    "'I cannot prove this from the available documents.'"
)

UNPROVEN_RESPONSE = "I cannot prove this from the available documents."

def get_api_key() -> str:
    """Retrieve Gemini API Key from environment or return empty string."""
    return os.getenv("GEMINI_API_KEY", "").strip()
