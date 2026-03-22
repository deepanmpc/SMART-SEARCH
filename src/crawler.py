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
                    "name": path.name,
                    "path": str(path),
                    "abs_path": str(path.resolve()),
                    "type": ext,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "created": stat.st_ctime,
                    "accessed": stat.st_atime,
                    "parent": str(path.parent)
                })
    
    return files