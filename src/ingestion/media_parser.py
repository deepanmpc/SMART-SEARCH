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

def chunk_video(video_path: str, threshold: float = 20.0, min_interval: int = 2, max_interval: int = 15) -> list[dict]:
    """
    Extracts frames using scene change detection.
    Optimized for CPU: Skips decoding frames using grab(), downscales frames to 128x128
    before computing differences to avoid heavy Numpy operations.
    """
    import numpy as np
    import cv2
    chunks = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return chunks

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    # Evaluate a frame roughly 4 times per min_interval
    frame_jump = max(1, int(fps * (min_interval / 4.0)))
    
    last_frame = None
    last_extracted_time = -min_interval
    frame_count = 0

    while True:
        # Fast-forward without decoding (saves immense CPU)
        success = cap.grab()
        if not success: break
        
        # Only decode the frame when we land on our jump interval
        if frame_count % frame_jump == 0:
            success, frame = cap.retrieve()
            if not success: break
            
            current_time = frame_count / fps
            time_since_last = current_time - last_extracted_time
            
            # Downscale for extremely fast pixel operations
            small_frame = cv2.resize(frame, (128, 128))
            
            extract = False
            if time_since_last >= min_interval:
                if time_since_last >= max_interval:
                    extract = True  # Fallback for static scenes
                elif last_frame is not None:
                    diff = cv2.absdiff(small_frame, last_frame)
                    score = np.mean(diff)
                    if score > threshold:
                        extract = True
                else:
                    extract = True

            if extract:
                # Retain the high-quality original frame for the embedding chunk
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    chunks.append({
                        "data": buffer.tobytes(),
                        "mime_type": "image/jpeg",
                        "suffix": f"sec_{int(current_time)}"
                    })
                    last_frame = small_frame
                    last_extracted_time = current_time
            elif time_since_last >= 1.0 and last_frame is not None:
                # Keep updating our baseline reference
                last_frame = small_frame
                
        frame_count += 1
    
    cap.release()
    return chunks
