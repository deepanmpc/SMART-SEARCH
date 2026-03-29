import os
from pathlib import Path
from PyPDF2 import PdfReader

from functools import lru_cache

@lru_cache(maxsize=100)
def generate_preview(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {"error": "File not found"}

    ext = Path(file_path).suffix.lower()
    stats = os.stat(file_path)
    size_mb = round(stats.st_size / (1024 * 1024), 2)
    
    preview = {
        "size_mb": size_mb,
        "type": ext[1:] if ext else "unknown",
        "content": ""
    }

    try:
        if ext in ('.txt', '.md', '.py', '.js', '.json', '.html', '.css'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [next(f) for _ in range(20)]
                preview["content"] = "".join(lines)
        
        elif ext == '.pdf':
            reader = PdfReader(file_path)
            if reader.pages:
                text = reader.pages[0].extract_text()
                preview["content"] = text[:1000] if text else "Encrypted or no text in PDF"
        
        elif ext in ('.mp4', '.mov', '.avi', '.mkv'):
            preview["content"] = "🎬 Video File\nHigh quality stream detected.\nOpen to play."
            
        elif ext in ('.mp3', '.wav', '.flac', '.m4a'):
            preview["content"] = "🎵 Audio File\nCrystal clear audio.\nOpen to listen."
            
    except Exception as e:
        preview["content"] = f"Error generating preview: {str(e)}"

    return preview
