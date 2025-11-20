from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Dict, Tuple, Any
from datetime import datetime

# ===== 기본 모델들 =====

class ServiceStatus(BaseModel):
    """서비스 상태"""
    name: str
    status: str
    last_check: Optional[datetime] = None

class SystemStatus(BaseModel):
    """전체 시스템 상태"""
    overall_status: str
    services: List[ServiceStatus]
    active_sessions: int

# ===== 대화 기록 =====
# Pydantic 모델 정의 (TypeScript의 인터페이스 역할)
# FIXME: 프론트앤드가 없는 상황에서 이 모델이 실제로 사용되는지 논의 필요
class Conversation(BaseModel):
    id: str  # 각 대화의 고유 ID (라우팅에 사용)
    title: str
    last_updated: str

# ================== dialogue-service 부분 ==================

class DialogueRequest(BaseModel):
    """소크라테스식 대화 요청"""
    session_id: str
    message: str
    conversation_history: Optional[List[str]] = []

# ================== strategy-service 부분 ==================

# ===== 라우팅 =====
# [!] 충돌 해결:
# 우리가 테스트한 'RoutingDecision' 모델 (213c214)을 선택하고,
# 충돌이 발생한 'RouteRequest' (HEAD)와 
# 그 짝이었던 'RouteResponse' (HEAD)는 제거합니다.

class RoutingDecision(BaseModel):
    """라우팅 결정 결과를 담는 모델"""
    route: str = Field(..., description="라우팅 경로 (e.g., 'rag_service', 'search_agent_service')")
    reason: str = Field(..., description="라우팅 결정 이유")


# ===== Strategy → Retrieval 요청 =====
class QueryOperator(str, Enum):
    """검색 연산자"""
    AND = "and"
    OR = "or"
    NOT = "not"

class RetrievalRoute(str, Enum):
    """검색 소스"""
    VECTOR_DB = "vector_book_db" # 국립중앙도서관 도서 벡터 DB
    YONSEI_HOLDINGS = "yonsei_holdings" # 연세대 도서관 소장 자료
    YONSEI_ELECTRONICS = "yonsei_electronics" # 연세대 도서관 전자자료

class SearchRequest(BaseModel):
    """Strategy Service가 Retrieval Service에 보내는 검색 요청"""
    
    # TODO: 서비스 사이 전달 부분이니 논의 필요
    # 일단 상정한 방법은 아래와 같음
    # 도서관 검색시 띄워쓰기 한 단어들은 적당히 검색되니까 이를 고려해서 설정
    queries: List[Tuple[str, QueryOperator]] = Field(
        ...,
        max_items=3, # 최대 3개 쿼리
        description="Multi-query/Step-back/HyDE로 변환된 쿼리들 (최대 3개)",
        example=[
            ("인공지능 윤리 의료 응용 최신 동향", QueryOperator.AND),
            ("AI ethics healthcare", QueryOperator.OR),
            ("privacy surveillance", QueryOperator.NOT),
        ],
    )
    routes: List[RetrievalRoute] = Field(
        ...,
        description="검색할 소스들 (도서관 소장, 전자자료, 벡터 DB 등)",
        example=[RetrievalRoute.VECTOR_DB, RetrievalRoute.YONSEI_HOLDINGS],
    )
    # 필터 부분은 전달 받아서 LLM에게 줘서 처리하는 방법 생각 중 - 어차피 메타데이터도 같이 넘길 것이니까?
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description=" (e.g. {'from': 2020, 'to': 2023, 'author': '홍길동'})"
    )
    top_k: int = Field(default=10, description="각 소스별 반환 문서 수")
    user_query: str = Field(description="원본 사용자 질문 (CRAG 평가용)")

# ================== retrieval-service 부분 ==================
# TODO: 전반적 수정 필요!

# ===== 검색된 문서 공통 모델 =====
class Document(BaseModel):
    """검색된 문서"""
    content: str = Field(description="문서 본문 텍스트")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="출처, 제목, 저자, URL 등"
    )
    score: float = Field(default=0.0, description="검색 유사도 점수")
    doc_id: Optional[str] = Field(default=None, description="문서 고유 ID")

# ===== 도서관 소장 정보 =====
class LibraryHoldingInfo(BaseModel):
    """도서관 소장 자료 상세 정보"""
    access_id: str = Field(..., description="자료 접근 ID (CATTOT...)")  
    title: str = Field(default="", description="자료 제목")
    author: str = Field(default="", description="저자(여러명도 한 문자열로 포함 가능)")
    material_type: str = Field(default="", description="자료 유형 (단행본, 연속간행물 등)")
    publication_info: str = Field(default="", description="발행 사항 (출판사, 발행지, 발행년도)")
    publication_year: int = Field(default=0, description="발행 연도")
    isbn: str = Field(default="", description="ISBN")
    book_description: str = Field(default="", description="책 소개 (일반 소개 + 출판사 제공 소개)")
    detail_url: str = Field(..., description="상세 정보 URL")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_id": "CATTOT000002202406",
                    "title": "(인공지능의) 윤리학",
                    "author": "이중원",
                    "material_type": "단행본",
                    "publication_info": "파주 : 한울아카데미, 2019",
                    "publication_year": 2019,
                    "isbn": "9788946071933",
                    "book_description": "인공지능 시대의 윤리적 문제를 다룬 책...",
                    "detail_url": "https://library.yonsei.ac.kr/search/detail/CATTOT000002202406"
                }
            ]
        }
    }

# ===== 도서관 전자자료 정보 =====
class ElectronicResourceInfo(BaseModel):
    """전자자료(학술논문, E-Book, 저널 등) 상세 정보"""
    access_id: str = Field(default="", description="자료 접근 ID (있는 경우)")
    title: str = Field(default="", description="자료 제목 (논문명, E-Book 제목 등)")
    author: List[str] = Field(default_factory=list, description="저자 또는 작성자")
    source: str = Field(default="", description="출판 정보 (저널명, 권호, 페이지 등)")
    publication_year: int = Field(default=0, description="출판년")
    doi: str = Field(default="", description="DOI (Digital Object Identifier)")
    link_url: str = Field(default="", description="원문 바로가기 링크 (Full Text URL)")
    abstract: str = Field(default="", description="초록 또는 요약 (있는 경우)")
    keywords: List[str] = Field(default_factory=list, description="키워드 목록(키워드랑 주제어 통합)")
    detail_url: str = Field(default="", description="상세 정보 URL (도서관 검색 결과 페이지)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_id": "",
                    "title": "Artificial Intelligence Ethics in the Context of Healthcare",
                    "author": "John Doe, Jane Smith",
                    "source": "Journal of Medical Ethics, Vol. 47, No. 3, pp. 123-135",
                    "publication_year": "2023",
                    "doi": "10.1136/medethics-2022-108234",
                    "link_url": "https://libproxy.yonsei.ac.kr/...",
                    "abstract": "This article explores the ethical implications of AI in healthcare...",
                    "keywords": ["artificial intelligence", "medical ethics", "healthcare"],
                    "detail_url": "https://library.yonsei.ac.kr/search/detail/..."
                }
            ]
        }
    }

# ===== Reranking 결과 =====
class RankedDocument(BaseModel):
    """Rerank 후 최종 문서"""
    
    content: str
    metadata: Dict[str, Any]
    rerank_score: float = Field(description="Cross-encoder 재점수")
    original_score: float = Field(description="초기 검색 점수")
    source: str = Field(description="데이터 소스 (vector_db/yonsei_library)")
    rank: int = Field(description="최종 순위 (1부터 시작)")

# ===== CRAG 평가 결과 =====
class RelevanceLevel(str, Enum):
    """CRAG 관련성 등급"""
    CORRECT = "correct"      # 바로 사용 가능
    AMBIGUOUS = "ambiguous"  # 보강 필요
    INCORRECT = "incorrect"  # 폐기

class CRAGResult(BaseModel):
    """CRAG 품질 평가 결과"""
    
    document: RankedDocument
    relevance: RelevanceLevel
    confidence: float = Field(ge=0.0, le=1.0, description="판단 신뢰도")
    reason: Optional[str] = Field(default=None, description="판단 근거")

# ===== Retrieval → Generation 응답 =====
class RetrievalResult(BaseModel):
    """Retrieval Service의 최종 응답"""
    
    documents: List[RankedDocument] = Field(
        description="CRAG 필터링 + Rerank 완료 문서"
    )
    crag_analysis: List[CRAGResult] = Field(
        description="전체 문서에 대한 CRAG 평가"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="검색 통계 (처리 시간, 소스별 문서 수 등)"
    )
    needs_web_search: bool = Field(
        default=False,
        description="CRAG에서 incorrect 비율이 높아 웹 검색 필요 여부"
    )

# ================== generation-service 부분 ==================