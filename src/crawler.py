from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}

def crawl_directory(folder_path):
    files = []
    
    for path in Path(folder_path).rglob("*"):
        if path.is_file():
            ext = path.suffix.lower()
            
            if ext in SUPPORTED_EXTENSIONS:
                stat = path.stat()
                
                files.append({
                    "filename": path.name,
                    "path": str(path),
                    "type": ext,
                    "modified": stat.st_mtime
                })
    
    return files