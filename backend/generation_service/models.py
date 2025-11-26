from pydantic import BaseModel, Field
from typing import List, Optional
from shared.models import RetrievalResult

class GenerationResult(BaseModel):
    """Final response from Generation Service"""
    answer: str = Field(description="Synthesized answer")
    citations: List[int] = Field(default=[], description="List of document indices cited")
    is_supported_score: int = Field(description="Self-evaluation: Support score (1-5)")
    is_useful_score: int = Field(description="Self-evaluation: Utility score (1-5)")
    reasoning: Optional[str] = Field(default=None, description="Reasoning for self-evaluation")
    
    # Metadata from retrieval for frontend display
    retrieval_metadata: Optional[dict] = Field(default=None)

class GenerationRequest(BaseModel):
    query: str = Field(description="Original user query")
    retrieval_result: RetrievalResult = Field(description="Result from Retrieval Service")
