import logging
from pathlib import Path
from typing import Dict, Any, List

# =========================
# Logging
# =========================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# Dependencies
# =========================

try:
    from PyPDF2 import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    logger.warning("Install PyPDF2")

try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("Install pytesseract pdf2image")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    logger.warning("Install python-docx")

try:
    from tika import parser
    TIKA_AVAILABLE = True
except ImportError:
    TIKA_AVAILABLE = False
    logger.warning("Install tika")


# =========================
# TEXT CHUNKING
# =========================

import re

import re

def chunk_text(text):

    # remove page markers
    text = re.sub(r"--- Page \d+ ---", "", text)

    # split numbered questions
    sections = re.split(r"\n\d+\.\s", text)

    chunks = []

    for section in sections:
        section = section.strip()

        # ignore headers or very small pieces
        if len(section) > 60:
            chunks.append(section)

    return chunks


# =========================
# PDF EXTRACTION
# =========================

def extract_pdf(file_path: str) -> str:

    if not PYPDF_AVAILABLE:
        return ""

    try:

        reader = PdfReader(file_path)
        text = ""

        for i, page in enumerate(reader.pages):

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

            elif OCR_AVAILABLE:

                images = convert_from_path(
                    file_path,
                    first_page=i + 1,
                    last_page=i + 1
                )

                if images:
                    text += pytesseract.image_to_string(images[0])

        return text

    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


# =========================
# DOCX EXTRACTION
# =========================

def extract_docx(file_path: str) -> str:

    if not DOCX_AVAILABLE:
        return ""

    try:

        doc = Document(file_path)
        text = ""

        for p in doc.paragraphs:
            text += p.text + "\n"

        for table in doc.tables:

            for row in table.rows:
                row_text = " | ".join(cell.text for cell in row.cells)
                text += row_text + "\n"

        return text

    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return ""


# =========================
# TXT EXTRACTION
# =========================

def extract_txt(file_path: str) -> str:

    try:

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    except Exception as e:
        logger.error(f"TXT extraction failed: {e}")
        return ""


# =========================
# TIKA FALLBACK
# =========================

def extract_with_tika(file_path: str) -> str:

    if not TIKA_AVAILABLE:
        return ""

    try:

        raw = parser.from_file(file_path)

        if raw and raw.get("content"):
            return raw["content"]

    except Exception as e:
        logger.error(f"Tika failed: {e}")

    return ""


# =========================
# UNIVERSAL EXTRACTOR
# =========================

def extract_any_document(file_path: str) -> Dict[str, Any]:

    path = Path(file_path)

    if not path.exists():

        return {
            "success": False,
            "error": "file not found"
        }

    text = ""

    # Select extractor
    if path.suffix.lower() == ".pdf":
        text = extract_pdf(file_path)

    elif path.suffix.lower() in [".docx", ".doc"]:
        text = extract_docx(file_path)

    elif path.suffix.lower() == ".txt":
        text = extract_txt(file_path)

    # Fallback to Tika
    if not text:
        text = extract_with_tika(file_path)

    if not text:

        return {
            "success": False,
            "error": "text extraction failed"
        }

    # Chunk the text
    chunks = chunk_text(text)

    return {
        "success": True,
        "file_path": file_path,
        "chunks": chunks
    }


# =========================
# CLI TEST
# =========================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print("Usage: python extractor.py <file>")
        exit()

    result = extract_any_document(sys.argv[1])

    if result["success"]:

        print(f"Extracted chunks: {len(result['chunks'])}")

        for c in result["chunks"][:2]:
            print("\nChunk preview:\n", c[:200])

    else:

        print("Error:", result["error"])