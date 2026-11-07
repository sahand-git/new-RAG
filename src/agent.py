"""
Gemini Document QA Agent with strict guardrails and structured citation extraction.
Enforces that all answers derive strictly from retrieved context chunks.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from src.config import (
    DEFAULT_GEMINI_MODEL,
    SYSTEM_PROMPT,
    UNPROVEN_RESPONSE,
    get_api_key,
)
from src.retriever import DocumentRetriever


@dataclass
class Citation:
    file_name: str
    page_number: int
    file_path: str = ""
    snippet: str = ""

    def __hash__(self):
        return hash((self.file_name, self.page_number))


@dataclass
class AgentResponse:
    query: str
    answer: str
    proven: bool
    citations: List[Citation] = field(default_factory=list)
    context_chunks: List[Dict[str, Any]] = field(default_factory=list)
    model_used: str = DEFAULT_GEMINI_MODEL
    raw_response: Optional[str] = None


class DocumentQAAgent:
    """Agent orchestrating retrieval, strict Gemini prompt execution, and citation parsing."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_GEMINI_MODEL,
        retriever: Optional[DocumentRetriever] = None,
    ):
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            raise ValueError("Gemini API key is required to initialize DocumentQAAgent.")

        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key)
        self.retriever = retriever or DocumentRetriever(api_key=self.api_key)

    def extract_citations(
        self,
        text: str,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> List[Citation]:
        """
        Extract citations from the response text and match them with known
        retrieved document paths.
        """
        citations_found: Dict[tuple, Citation] = {}

        # Build lookup table of file_name -> file_path from retrieved chunks
        path_map: Dict[str, str] = {}
        for c in retrieved_chunks:
            fname = c.get("file_name", "")
            fpath = c.get("file_path", "")
            if fname and fpath:
                path_map[fname] = fpath
                path_map[fname.lower()] = fpath

        # Regex pattern 1: [Document.pdf, Page 41] or [Manual_P200, Page 41]
        pattern_bracket = re.compile(
            r"\[\s*([^,\]]+?)\s*,\s*(?:Page|p\.?)\s*(\d+)\s*\]",
            re.IGNORECASE,
        )
        for match in pattern_bracket.finditer(text):
            doc_name = match.group(1).strip()
            page_num = int(match.group(2).strip())

            # Ensure .pdf suffix if matched without
            if not doc_name.lower().endswith(".pdf"):
                candidate = f"{doc_name}.pdf"
                if candidate in path_map:
                    doc_name = candidate

            doc_path = path_map.get(doc_name, path_map.get(doc_name.lower(), ""))
            key = (doc_name, page_num)
            if key not in citations_found:
                citations_found[key] = Citation(
                    file_name=doc_name,
                    page_number=page_num,
                    file_path=doc_path,
                )

        # Regex pattern 2: Manual_P200.pdf, Page 41 (outside brackets)
        pattern_free = re.compile(
            r"\b([a-zA-Z0-9_\-\.]+\.pdf)[,\s]+(?:Page|p\.?)\s*(\d+)\b",
            re.IGNORECASE,
        )
        for match in pattern_free.finditer(text):
            doc_name = match.group(1).strip()
            page_num = int(match.group(2).strip())
            doc_path = path_map.get(doc_name, path_map.get(doc_name.lower(), ""))
            key = (doc_name, page_num)
            if key not in citations_found:
                citations_found[key] = Citation(
                    file_name=doc_name,
                    page_number=page_num,
                    file_path=doc_path,
                )

        # If model answered affirmatively but didn't output bracket tags,
        # fallback to top retrieved chunk sources
        if not citations_found and retrieved_chunks and UNPROVEN_RESPONSE not in text:
            for c in retrieved_chunks[:2]:
                key = (c["file_name"], c["page_number"])
                if key not in citations_found:
                    citations_found[key] = Citation(
                        file_name=c["file_name"],
                        page_number=c["page_number"],
                        file_path=c.get("file_path", ""),
                        snippet=c["text"][:120],
                    )

        return list(citations_found.values())

    def answer_query(
        self,
        query: str,
        top_k: int = 4,
        filter_document: Optional[str] = None,
    ) -> AgentResponse:
        """
        Execute full RAG question-answering workflow:
        1. Retrieve top-K relevant chunks.
        2. Format context with page metadata.
        3. Prompt Gemini with strict guardrails.
        4. Parse and return structured answer with visual citation triggers.
        """
        # Retrieve context chunks
        chunks = self.retriever.retrieve(
            query=query,
            top_k=top_k,
            filter_document=filter_document,
        )

        if not chunks:
            return AgentResponse(
                query=query,
                answer=UNPROVEN_RESPONSE,
                proven=False,
                citations=[],
                context_chunks=[],
                model_used=self.model_name,
            )

        context_text = self.retriever.format_context_for_prompt(chunks)

        user_prompt = f"""DOCUMENT CONTEXT:
{context_text}

USER QUESTION:
{query}

CRITICAL INSTRUCTIONS:
- Base your answer ONLY on the technical documents provided above.
- Cite specific page references using the exact format: [Document Name, Page X].
- If the question cannot be definitively and factually proven from the provided document excerpts, you MUST reply with EXACTLY:
"{UNPROVEN_RESPONSE}"
- Do not speculate, extrapolate, or use outside knowledge.
"""

        try:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.0,  # Zero temperature for maximum factual precision
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config,
            )

            raw_answer = response.text.strip() if response.text else UNPROVEN_RESPONSE
            proven = UNPROVEN_RESPONSE.lower() not in raw_answer.lower()
            citations = self.extract_citations(raw_answer, chunks) if proven else []

            return AgentResponse(
                query=query,
                answer=raw_answer,
                proven=proven,
                citations=citations,
                context_chunks=chunks,
                model_used=self.model_name,
                raw_response=raw_answer,
            )

        except Exception as exc:
            return AgentResponse(
                query=query,
                answer=f"Error executing Gemini request: {str(exc)}",
                proven=False,
                citations=[],
                context_chunks=chunks,
                model_used=self.model_name,
            )
