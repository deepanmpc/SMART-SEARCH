from google import genai
from google.genai import types

# For Vertex AI:
# PROJECT_ID='<add_here>'
# client = genai.Client(vertexai=True, project=PROJECT_ID, location='us-central1')

client = genai.Client()

with open("example.png", "rb") as f:
    image_bytes = f.read()

with open("sample.mp3", "rb") as f:
    audio_bytes = f.read()

# Embed text, image, and audio 
result = client.models.embed_content(
    model="gemini-embedding-2-preview",
    contents=[
        "What is the meaning of life?",
        types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png",
        ),
        types.Part.from_bytes(
            data=audio_bytes,
            mime_type="audio/mpeg",
        ),
    ],
)

print(result.embeddings)