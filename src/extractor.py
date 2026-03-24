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
# Chunking
# =========================

def chunk_text(text: str, chunk_size=400, overlap=50) -> List[str]:

    words = text.split()
    chunks = []

    start = 0

    while start < len(words):

        end = start + chunk_size
        chunk = " ".join(words[start:end])

        if len(chunk.strip()) > 30:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# =========================
# PDF Extraction
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
# DOCX Extraction
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
# TXT Extraction
# =========================

def extract_txt(file_path: str) -> str:

    try:

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    except Exception as e:
        logger.error(f"TXT extraction failed: {e}")
        return ""


# =========================
# Tika fallback
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
# Universal extractor
# =========================

def extract_any_document(file_path: str) -> Dict[str, Any]:

    path = Path(file_path)

    if not path.exists():

        return {
            "success": False,
            "error": "file not found"
        }

    text = ""

    if path.suffix.lower() == ".pdf":
        text = extract_pdf(file_path)

    elif path.suffix.lower() in [".docx", ".doc"]:
        text = extract_docx(file_path)

    elif path.suffix.lower() == ".txt":
        text = extract_txt(file_path)

    if not text:
        text = extract_with_tika(file_path)

    if not text:

        return {
            "success": False,
            "error": "text extraction failed"
        }

    chunks = chunk_text(text)

    return {
        "success": True,
        "file_path": file_path,
        "chunks": chunks
    }


# =========================
# CLI
# =========================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print("Usage: python extractor.py <file>")
        exit()

    result = extract_any_document(sys.argv[1])

    if result["success"]:
        print("Extracted chunks:", len(result["chunks"]))
    else:
        print("Error:", result["error"])