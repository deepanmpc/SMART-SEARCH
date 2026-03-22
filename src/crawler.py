from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

def crawl_directory(folder_path):
    files = []
    
    for path in Path(folder_path).rglob("*"):
        if path.is_file():
            ext = path.suffix.lower()
            
            if ext in SUPPORTED_EXTENSIONS:
                files.append({
                    "path": str(path),
                    "type": ext,
                    "modified": path.stat().st_mtime
                })
    
    return files