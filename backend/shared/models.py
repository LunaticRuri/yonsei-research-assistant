from pydantic import BaseModel, Field, model_validator
from enum import Enum
from typing import List, Optional, Dict, Union, Any
from datetime import datetime

# ===== 기본 모델들 =====

class ServiceStatus(BaseModel):
    name: str
    status: str
    last_check: Optional[datetime] = None

class SystemStatus(BaseModel):
    overall_status: str
    services: List[ServiceStatus]
    active_sessions: int

# ===== 대화 기록 =====
class Conversation(BaseModel):
    id: str  # 각 대화의 고유 ID (라우팅에 사용)
    title: str
    last_updated: str

# ================== dialogue-service 부분 ==================

class DialogueRequest(BaseModel):
    session_id: str
    message: str
    conversation_history: Optional[List[str]] = []

# ================== strategy-service 부분 ==================

class RoutingDecision(BaseModel):
    route: str = Field(..., description="라우팅 경로 (e.g., 'rag_service', 'search_agent_service')")
    reason: str = Field(..., description="라우팅 결정 이유")
    
    search_queries: List[str] = Field(
        default=[],
        description="검색 엔진에 입력할 최적화된 키워드 리스트 (예: ['굴패각 활용', '석회석 소성'])"
    )

# ================== retrieval-service 부분 ==================

class QueryOperator(str, Enum):
    AND = "and" 
    OR = "or"   
    NOT = "not" 

class RetrievalRoute(str, Enum):
    VECTOR_DB = "vector_book_db" 
    YONSEI_HOLDINGS = "yonsei_holdings" 
    YONSEI_ELECTRONICS = "yonsei_electronics" 


class LibrarySearchField(str, Enum):
    TOTAL = "TOTAL"  
    TITLE = "1"  
    AUTHOR = "2"  
    PUBLISHER = "3"  
    SUBJECT = "4"  

class HoldingsMaterialType(str, Enum):
    TOTAL = "TOTAL"  
    BOOK = "m"  
    SERIAL = "s"  
    MULTIMEDIA = "b;p;v;x;u;c"  
    THESIS = "t"  
    OLD_BOOK = "o"  
    ARTICLE = "zart"  

class ElectronicSearchField(str, Enum):
    TOTAL = ""       
    KEYWORD = "TX"  
    TITLE = "TI"     
    AUTHOR = "AU"    
    SUBJECT = "SU"  

class SearchQueries(BaseModel):
    query_1: str
    search_field_1: Union[str, LibrarySearchField, ElectronicSearchField]
    operator_1: Optional[QueryOperator] = None
    query_2: Optional[str] = None
    search_field_2: Optional[Union[str, LibrarySearchField, ElectronicSearchField]] = None
    operator_2: Optional[QueryOperator] = None
    query_3: Optional[str] = None
    search_field_3: Optional[Union[str, LibrarySearchField, ElectronicSearchField]] = None
    
    @model_validator(mode='after')
    def validate_query_sequence(self):
        has_query_2 = bool(self.query_2)
        has_query_3 = bool(self.query_3)
        
        if not has_query_2 and has_query_3:
            raise ValueError(
                "Invalid query sequence: query_3 cannot exist without query_2. "
                "Valid combinations: (query_1), (query_1, query_2), (query_1, query_2, query_3)"
            )
        
        if has_query_2:
            if self.search_field_2 is None:
                raise ValueError("search_field_2 is required when query_2 is provided")
            
        if has_query_3:
            if self.operator_2 is None:
                raise ValueError("operator_2 is required when query_3 is provided")
            if self.search_field_3 is None:
                raise ValueError("search_field_3 is required when query_3 is provided")
        
        return self


class SearchRequest(BaseModel):
    queries: SearchQueries = Field(..., description="Multi-query/Step-back/HyDE 등으로 변환된 쿼리들 (최대 3개)")
    routes: List[RetrievalRoute] = Field(
        ...,
        description="검색할 소스들 (도서관 소장, 전자자료, 벡터 DB 등)",
        examples=[
            [RetrievalRoute.VECTOR_DB, RetrievalRoute.YONSEI_HOLDINGS],
            [RetrievalRoute.YONSEI_ELECTRONICS]
        ],
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="각 소스별 필터 조건 (연도 범위, 자료 유형 등)",
        examples=[
            {"year_range": (2020, 2023), "material_types": [HoldingsMaterialType.BOOK, HoldingsMaterialType.THESIS]},
            {"year_range": (2023, 2025), "academic_journals_only": False, "foreign_language": False} 
        ]
    )
    top_k: int = Field(default=10, description="각 소스별 반환 문서 수")
    user_query: str = Field(description="원본 사용자 질문 (CRAG 평가용)")

# ===== 검색된 문서 공통 모델 =====
class Document(BaseModel):
    content: str = Field(description="문서 본문 텍스트")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="출처, 제목, 저자, URL 등"
    )
    score: float = Field(default=0.0, description="검색 유사도 점수")
    doc_id: Optional[str] = Field(default=None, description="문서 고유 ID")

# ===== 도서관 소장 정보 =====

class LibraryHoldingInfo(BaseModel):
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
    content: str
    metadata: Dict[str, Any]
    rerank_score: float = Field(description="Cross-encoder 재점수")
    original_score: float = Field(description="초기 검색 점수")
    source: str = Field(description="데이터 소스 (vector_db/yonsei_library)")
    rank: int = Field(description="최종 순위 (1부터 시작)")

# ===== CRAG 평가 결과 =====
class AnalysisUserQuery(BaseModel):
    topic: str = Field(description="주제")
    intent: str = Field(description="의도")
    constraints: Optional[str] = Field(default=None, description="제약 조건 (있는 경우)")

class RelevanceLevel(str, Enum):
    CORRECT = "correct"      
    AMBIGUOUS = "ambiguous"  
    INCORRECT = "incorrect"  

class GeneratedCRAGResponse(BaseModel):
    relevance: RelevanceLevel = Field(description="문서 관련성 등급")
    confidence: float = Field(ge=0.0, le=1.0, description="판단 신뢰도")
    reason: Optional[str] = Field(default=None, description="판단 근거")

class CRAGResult(BaseModel):
    document: RankedDocument
    relevance: RelevanceLevel
    confidence: float = Field(ge=0.0, le=1.0, description="판단 신뢰도")
    reason: Optional[str] = Field(default=None, description="판단 근거")

# ================== generation-service 부분 ==================

class RetrievalResult(BaseModel):
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
    needs_requestioning: bool = Field(
        default=False,
        description="CRAG에서 incorrect 비율이 높아 질문 수정 또는 재검색 필요 여부"
    )

# ================== [New] 추가: 간편 연동용 모델 ==================

class SimpleSearchRequest(BaseModel):
    """
    Strategy -> Retrieval 간편 연동을 위한 단순 요청 모델
    (복잡한 필드 지정 없이 키워드 리스트만으로 검색 요청)
    """
    query: str              # 사용자의 원래 질문 (참고용)
    keywords: List[str]     # 추출된 키워드 리스트 (예: ["디지털 리터러시", "노인"])
    top_k: int = 5          # 반환할 문서 개수
    
    # 선택 사항: 검색 소스 지정 (기본값: 벡터DB, 도서관 소장자료)
    routes: List[RetrievalRoute] = Field(
        default=[RetrievalRoute.VECTOR_DB, RetrievalRoute.YONSEI_HOLDINGS],
        description="검색할 대상 소스"
    )
