from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ===== 기본 모델들 =====

class DialogueRequest(BaseModel):
    """소크라테스식 대화 요청"""
    session_id: str
    message: str
    conversation_history: Optional[List[str]] = []

class DialogueResponse(BaseModel):
    """소크라테스식 대화 응답"""
    session_id: str
    response_text: str
    conversation_stage: int
    follow_up_questions: List[str] = []
    insights: List[str] = []
    topic_clarity_score: Optional[int] = None

# ===== 검색 전략 관련 =====

class SearchStrategy(BaseModel):
    """검색 전략"""
    primary_keywords: List[str]
    expansion_keywords: List[str] = []
    boolean_query: Optional[str] = None
    rationale: str
    academic_fields: List[str] = []
    suggested_databases: List[str] = []

class StrategyGenerationRequest(BaseModel):
    """전략 생성 요청"""
    session_id: str
    conversation_summary: str
    research_topic: str
    key_concepts: List[str]

class StrategyUpdateRequest(BaseModel):
    """전략 업데이트 요청"""
    session_id: str
    current_strategy: SearchStrategy
    modifications: Dict[str, Any]
    feedback: str

class SearchStrategyResponse(BaseModel):
    """검색 전략 응답"""
    session_id: str
    strategy: SearchStrategy
    confidence_score: float
    alternative_approaches: List[Dict[str, str]] = []

# ===== RAG 관련 =====

class RAGAnalysisRequest(BaseModel):
    """RAG 분석 요청"""
    session_id: str
    search_strategy: SearchStrategy
    analysis_depth: Optional[str] = "standard"  # "standard" or "detailed"

class DocumentResult(BaseModel):
    """문서 결과"""
    title: str
    authors: List[str]
    publication_year: int
    source: str
    abstract: str
    relevance_score: float
    yonsei_library_status: str
    access_link: str

class RAGAnalysisResponse(BaseModel):
    """RAG 분석 응답"""
    session_id: str
    analysis_summary: str
    key_debates: List[Dict[str, str]]
    relevant_documents: List[DocumentResult]
    confidence_score: float
    search_strategy_used: SearchStrategy
    analysis_limitations: str

# ===== 도서관 검색 관련 =====

class LibrarySearchRequest(BaseModel):
    """도서관 검색 요청"""
    session_id: str
    search_strategy: SearchStrategy
    max_results: Optional[int] = 20

class LibrarySearchResponse(BaseModel):
    """도서관 검색 응답"""
    session_id: str
    search_query_used: str
    total_found: int
    results: List[DocumentResult]
    search_summary: str
    recommendations: List[str]

# ===== 세션 관리 =====

class SessionInfo(BaseModel):
    """세션 정보"""
    session_id: str
    created_at: datetime
    current_stage: int  # 1: 대화, 2: 전략, 3: RAG, 4: 검색
    research_topic: Optional[str] = None
    last_activity: datetime

class SessionSummary(BaseModel):
    """세션 요약"""
    session_id: str
    research_topic: str
    key_insights: List[str]
    final_strategy: Optional[SearchStrategy] = None
    document_count: int
    completed_stages: List[int]

# ===== 오류 응답 =====

class ErrorResponse(BaseModel):
    """오류 응답"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None

# ===== 서비스 상태 =====

class ServiceStatus(BaseModel):
    """서비스 상태"""
    service_name: str
    status: str  # "healthy", "degraded", "down"
    version: str
    uptime: float
    last_check: datetime

class SystemStatus(BaseModel):
    """전체 시스템 상태"""
    overall_status: str
    services: List[ServiceStatus]
    active_sessions: int