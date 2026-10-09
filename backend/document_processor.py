"""
FloatingTextbook AI — Document Processor & Textbook Ingestion Engine
=====================================================================
Supports:
- PDF (via PyMuPDF / fitz, with fallback to pypdf)
- Plain Text (TXT, Markdown, Notes)
- Structural chunking preserving exact page numbers and headings
- Topic extraction and keyword indexing
- Grounded citation retrieval (RAG) returning verbatim excerpts with page citations
"""

import os
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple
from backend.database import get_db_connection


class DocumentProcessor:
    def __init__(self):
        # Verify available PDF parsing library
        self.has_fitz = False
        try:
            import pymupdf as fitz
            self.has_fitz = True
        except ImportError:
            try:
                import fitz
                self.has_fitz = True
            except ImportError:
                pass

    def extract_text_from_file(self, file_path: str, filename: str) -> List[Dict[str, Any]]:
        """
        Extracts text from a document page-by-page, preserving page numbers and formatting.
        Returns a list of page dicts: [{"page_number": int, "text": str}]
        """
        ext = os.path.splitext(filename)[1].lower()
        pages = []

        if ext == ".pdf":
            pages = self._extract_pdf(file_path)
        elif ext in [".txt", ".md", ".json"]:
            pages = self._extract_text(file_path)
        else:
            # Fallback text reading
            pages = self._extract_text(file_path)

        # Post-process pages: clean whitespace, detect empty/scanned documents
        cleaned_pages = []
        for p in pages:
            raw = p.get("text", "")
            # Normalization: normalize excessive spaces while preserving paragraphs
            normalized = re.sub(r'[ \t]+', ' ', raw)
            normalized = re.sub(r'\n{3,}', '\n\n', normalized).strip()
            if normalized:
                cleaned_pages.append({
                    "page_number": p["page_number"],
                    "text": normalized
                })

        return cleaned_pages

    def _extract_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        pages = []
        if self.has_fitz:
            import fitz
            try:
                doc = fitz.open(file_path)
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    text = page.get_text("text")
                    pages.append({
                        "page_number": page_idx + 1,
                        "text": text
                    })
                doc.close()
                return pages
            except Exception as e:
                print(f"[DocProcessor] PyMuPDF error: {e}, attempting pypdf fallback")

        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append({
                    "page_number": page_idx + 1,
                    "text": text
                })
        except Exception as e:
            print(f"[DocProcessor] pypdf error: {e}")

        return pages

    def _extract_text(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        # Split into ~2000-char logical "pages" for consistent paging experience
        chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
        if not chunks:
            chunks = [""]
        return [{"page_number": idx + 1, "text": chunk} for idx, chunk in enumerate(chunks)]

    def chunk_and_index_document(self, doc_id: str, pages: List[Dict[str, Any]], default_topic: str = "General") -> List[Dict[str, Any]]:
        """
        Splits page text into coherent chunks (~300-500 words), detects headings,
        and saves chunks into database.
        """
        conn = get_db_connection()
        cur = conn.cursor()
        saved_chunks = []

        heading_regex = re.compile(r'^(?:[0-9]+\.?[0-9]*\s+)?([A-Z][A-Za-z0-9\s,\-–—:]{3,60})$', re.MULTILINE)

        for page in pages:
            page_num = page["page_number"]
            text = page["text"]

            # Detect headings on page
            headings = heading_regex.findall(text)
            current_heading = headings[0].strip() if headings else f"Page {page_num} Section"

            # Split paragraphs
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
            if not paragraphs:
                paragraphs = [text] if text else []

            # Group into chunks
            chunk_buffer = []
            chunk_char_count = 0

            for para in paragraphs:
                chunk_buffer.append(para)
                chunk_char_count += len(para)

                if chunk_char_count >= 600:
                    chunk_text = "\n\n".join(chunk_buffer)
                    chunk_id = f"chk-{uuid.uuid4().hex[:8]}"

                    cur.execute("""
                    INSERT INTO document_chunks (id, document_id, page_number, topic, heading, content)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (chunk_id, doc_id, page_num, default_topic, current_heading, chunk_text))

                    saved_chunks.append({
                        "id": chunk_id,
                        "page_number": page_num,
                        "heading": current_heading,
                        "content": chunk_text
                    })
                    chunk_buffer = []
                    chunk_char_count = 0

            if chunk_buffer:
                chunk_text = "\n\n".join(chunk_buffer)
                chunk_id = f"chk-{uuid.uuid4().hex[:8]}"
                cur.execute("""
                INSERT INTO document_chunks (id, document_id, page_number, topic, heading, content)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (chunk_id, doc_id, page_num, default_topic, current_heading, chunk_text))
                saved_chunks.append({
                    "id": chunk_id,
                    "page_number": page_num,
                    "heading": current_heading,
                    "content": chunk_text
                })

        conn.commit()
        conn.close()
        return saved_chunks

    def extract_topics_from_text(self, pages: List[Dict[str, Any]], doc_id: str, subject: str = "Science") -> List[Dict[str, Any]]:
        """
        Extracts key topics and concept clusters from the document text.
        """
        # Look for chapter/section headers or recurring key terms
        extracted_topics = []
        topic_candidates = {}

        for p in pages:
            lines = [l.strip() for l in p["text"].split("\n") if l.strip()]
            for line in lines[:5]:
                # Check if line looks like a title/chapter
                if len(line) < 60 and not line.endswith((".", ":", ";")) and re.match(r'^[A-Z0-9]', line):
                    if line not in topic_candidates:
                        topic_candidates[line] = []
                    topic_candidates[line].append(p["page_number"])

        conn = get_db_connection()
        cur = conn.cursor()
        now = uuid.uuid4().hex[:6]

        # Filter top candidates
        valid_topics = [t for t, pages_seen in topic_candidates.items() if 4 <= len(t) <= 50][:5]
        if not valid_topics:
            valid_topics = ["Fundamental Concepts", "Theoretical Foundations", "Practical Applications"]

        for idx, t_name in enumerate(valid_topics):
            top_id = f"top-up-{now}-{idx}"
            pages_list = topic_candidates.get(t_name, [1])
            page_range = f"pp. {min(pages_list)}-{max(pages_list)}" if pages_list else "p. 1"
            summary = f"Core topic extracted from textbook focusing on {t_name}."

            cur.execute("""
            INSERT INTO topics (id, subject, title, summary, document_id, page_range, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (top_id, subject, t_name, summary, doc_id, page_range))

            extracted_topics.append({
                "id": top_id,
                "title": t_name,
                "subject": subject,
                "page_range": page_range,
                "summary": summary
            })

        conn.commit()
        conn.close()
        return extracted_topics

    def search_grounded_chunks(self, query: str, document_id: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        BM25 / lexical keyword matching across document chunks to retrieve exact source excerpts
        with page citations.
        """
        conn = get_db_connection()
        cur = conn.cursor()

        # Tokenize query
        keywords = [k.lower() for k in re.findall(r'\b[A-Za-z]{3,}\b', query)]
        if not keywords:
            keywords = ["learning"]

        query_sql = """
        SELECT c.id, c.document_id, c.page_number, c.topic, c.heading, c.content, d.title as doc_title
        FROM document_chunks c
        LEFT JOIN documents d ON c.document_id = d.id
        """
        params = []
        if document_id:
            query_sql += " WHERE c.document_id = ?"
            params.append(document_id)

        cur.execute(query_sql, params)
        rows = cur.fetchall()
        conn.close()

        scored_chunks = []
        for r in rows:
            content_lower = r["content"].lower()
            topic_lower = (r["topic"] or "").lower()
            heading_lower = (r["heading"] or "").lower()

            score = 0
            for kw in keywords:
                if kw in content_lower:
                    score += content_lower.count(kw) * 1.0
                if kw in heading_lower:
                    score += 3.0
                if kw in topic_lower:
                    score += 2.0

            if score > 0:
                scored_chunks.append({
                    "id": r["id"],
                    "document_id": r["document_id"],
                    "document_title": r["doc_title"] or "Textbook",
                    "page_number": r["page_number"],
                    "topic": r["topic"],
                    "heading": r["heading"],
                    "content": r["content"],
                    "score": score
                })

        # Sort by relevance score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:limit]
