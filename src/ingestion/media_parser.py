"""
Media parser — Handles advanced chunking for images and videos.
Images: Large images are tiled into smaller overlapping chunks.
Videos: Temporal chunking via keyframe extraction (e.g., 1 frame every 5 seconds).
"""

import io
from PIL import Image
import cv2

def chunk_image(image_bytes: bytes, max_dim: int = 1024, overlap: int = 256) -> list[dict]:
    """
    If the image is larger than `max_dim` in either dimension, it crops the 
    image into overlapping tiles. Otherwise, it returns the whole image.
    Returns a list of dicts: {"data": bytes, "mime_type": "image/jpeg", "suffix": str}
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        # Fallback if Pillow can't open it
        return [{"data": image_bytes, "mime_type": "image/jpeg", "suffix": "full"}]

    width, height = img.size
    if width <= max_dim and height <= max_dim:
        return [{"data": image_bytes, "mime_type": "image/jpeg", "suffix": "full"}]

    chunks = []
    y = 0
    while y < height:
        x = 0
        while x < width:
            box = (x, y, min(x + max_dim, width), min(y + max_dim, height))
            tile = img.crop(box)
            
            buf = io.BytesIO()
            tile.save(buf, format="JPEG")
            chunks.append({
                "data": buf.getvalue(),
                "mime_type": "image/jpeg",
                "suffix": f"tile_{x}_{y}"
            })
            
            x += (max_dim - overlap)
        y += (max_dim - overlap)

    return chunks

def chunk_video(video_path: str, interval_sec: int = 5) -> list[dict]:
    """
    Extracts 1 frame every `interval_sec` seconds from a video.
    Returns a list of dicts: {"data": bytes, "mime_type": "image/jpeg", "suffix": str}
    """
    chunks = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return chunks

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # fallback

    frame_interval = int(fps * interval_sec)
    frame_count = 0
    success, frame = cap.read()

    while success:
        if frame_count % frame_interval == 0:
            # Convert frame to JPEG bytes
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                sec = int(frame_count / fps)
                chunks.append({
                    "data": buffer.tobytes(),
                    "mime_type": "image/jpeg",
                    "suffix": f"sec_{sec}"
                })
        
        success, frame = cap.read()
        frame_count += 1

    cap.release()
    return chunks
