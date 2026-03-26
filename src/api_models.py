from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    file_type: Optional[str] = None

class SearchResult(BaseModel):
    document_name: str
    file_path: Optional[str] = None
    file_type: str
    content_type: str = "text"
    chunk_text: Optional[str]
    score: float

class SearchResponse(BaseModel):
    results: List[SearchResult]

class IndexRequest(BaseModel):
    paths: List[str]

class IndexResponse(BaseModel):
    success: bool
    message: str
    files_indexed: int
    chunks_indexed: int

class StatsResponse(BaseModel):
    total_chunks: int
    plan: str
    plan_limit: int
    usage_percent: float

class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    file_type: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    sources: List[SearchResult]

class IndexStatusResponse(BaseModel):
    is_indexing: bool
    is_paused: bool = False
    current_file: str
    total_files: int
    processed_files: int
    percentage: float
    eta_seconds: float
