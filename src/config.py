import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure the Google GenAI SDK targets v1beta (where text-embedding-004 resides)
os.environ.setdefault("GOOGLE_GENAI_API_VERSION", "v1beta")

# Load environment variables from .env file
load_dotenv()

# Base project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", str(BASE_DIR / "documents"))).resolve()
VECTOR_DB_DIR = Path(os.getenv("CHROMA_DB_DIR", str(BASE_DIR / "vector_db"))).resolve()

# Gemini Models (Updated to newest Gemini 3.8 Flash & Gemini Embedding 001)
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

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


def create_genai_client(api_key: str):
    """
    Create a Gemini Client configured with v1beta endpoint to support
    text-embedding-004 and modern multimodal capabilities.
    """
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )

