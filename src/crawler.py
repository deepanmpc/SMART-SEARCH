from pathlib import Path

SUPPORTED_EXTENSIONS = {
    # Documents
    ".pdf": "pdf", ".docx": "docx", ".doc": "docx", ".txt": "text",
    ".pptx": "pptx", ".ppt": "pptx", ".md": "text", ".rtf": "text",
    # Code Files
    ".py": "text", ".js": "text", ".ts": "text", ".c": "text", ".cpp": "text",
    ".h": "text", ".html": "text", ".css": "text", ".json": "text",
    ".yaml": "text", ".yml": "text", ".sh": "text", ".sql": "text",
    # Images
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".webp": "image",
    ".gif": "image", ".bmp": "image",
    # Video
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
    # Audio
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".flac": "audio",
}

SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules"}


def crawl_directory(folder_path: str) -> list[dict]:
    files = []
    for path in Path(folder_path).rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            stat = path.stat()
            files.append({
                "filename": path.name,
                "path": str(path),
                "type": SUPPORTED_EXTENSIONS[path.suffix.lower()],
                "ext": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
            })
    return files