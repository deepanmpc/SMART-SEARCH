"""
Media router — routes files by type for multimodal embedding.

- Images/Video/Audio → raw bytes (sent directly to Gemini)
- Small PDFs (≤6 pages) → raw bytes
- Large PDFs/DOCX/TXT → text extraction + chunking
"""

from pathlib import Path

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


def _read_bytes(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def _get_pdf_page_count(file_path: str) -> int:
    if not PYPDF_AVAILABLE:
        return 999
    try:
        return len(PdfReader(file_path).pages)
    except Exception:
        return 999


def _extract_docx_text(file_path: str) -> str:
    if not DOCX_AVAILABLE:
        return ""
    doc = Document(file_path)
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return "\n".join(parts)


def _chunk_text(text: str, chunk_size: int = 500) -> list[str]:
    """Word-based chunker with overlap for long text documents."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - 50):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.strip()) > 50:
            chunks.append(chunk)
    return chunks


def prepare_for_embedding(file_meta: dict) -> list[dict]:
    """
    Returns a list of 'embedding units'. Each unit is either:
      - {"type": "bytes", "data": bytes, "mime_type": str}
      - {"type": "text", "data": str}
    """
    path = file_meta["path"]
    file_type = file_meta["type"]
    ext = file_meta["ext"]

    if file_type == "image":
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        return [{"type": "bytes", "data": _read_bytes(path), "mime_type": mime}]

    if file_type == "video":
        mime = "video/mp4" if ext == ".mp4" else "video/quicktime"
        return [{"type": "bytes", "data": _read_bytes(path), "mime_type": mime}]

    if file_type == "audio":
        mime_map = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4"}
        return [{"type": "bytes", "data": _read_bytes(path), "mime_type": mime_map.get(ext, "audio/mpeg")}]

    if file_type == "pdf":
        page_count = _get_pdf_page_count(path)
        if page_count <= 6:
            return [{"type": "bytes", "data": _read_bytes(path), "mime_type": "application/pdf"}]
        else:
            if PYPDF_AVAILABLE:
                reader = PdfReader(path)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                return [{"type": "text", "data": c} for c in _chunk_text(text)]
            return []

    if file_type == "docx":
        text = _extract_docx_text(path)
        return [{"type": "text", "data": c} for c in _chunk_text(text)]

    if file_type == "text":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return [{"type": "text", "data": c} for c in _chunk_text(text)]

    return []
