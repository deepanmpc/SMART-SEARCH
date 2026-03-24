"""
Document parser — extracts raw text from PDF, DOCX, TXT.
Always returns text for chunking (no raw-bytes path).
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from PyPDF2 import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from tika import parser
    TIKA_AVAILABLE = True
except ImportError:
    TIKA_AVAILABLE = False


def extract_pdf(file_path: str) -> str:
    if not PYPDF_AVAILABLE:
        return ""
    try:
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


def extract_docx(file_path: str) -> str:
    if not DOCX_AVAILABLE:
        return ""
    try:
        doc = Document(file_path)
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return ""


def extract_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logger.error(f"TXT extraction failed: {e}")
        return ""


def extract_with_tika(file_path: str) -> str:
    if not TIKA_AVAILABLE:
        return ""
    try:
        raw = parser.from_file(file_path)
        return raw.get("content", "") if raw else ""
    except Exception as e:
        logger.error(f"Tika failed: {e}")
        return ""


def parse_document(file_path: str) -> dict:
    """
    Extract text from any supported document.
    Returns {"success": bool, "text": str, "error": str}
    """
    path = Path(file_path)

    if not path.exists():
        return {"success": False, "text": "", "error": "file not found"}

    ext = path.suffix.lower()
    text = ""

    if ext == ".pdf":
        text = extract_pdf(file_path)
    elif ext in (".docx", ".doc"):
        text = extract_docx(file_path)
    elif ext == ".txt":
        text = extract_txt(file_path)

    if not text:
        text = extract_with_tika(file_path)

    if not text or not text.strip():
        return {"success": False, "text": "", "error": "extraction failed"}

    return {"success": True, "text": text}
