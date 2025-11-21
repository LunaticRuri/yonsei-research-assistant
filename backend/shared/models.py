from pydantic import BaseModel, Field, model_validator
from enum import Enum
from typing import List, Optional, Dict, Union, Any
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

# ================== retrieval-service 부분 ==================

# ===== Strategy → Retrieval 요청 =====
class QueryOperator(str, Enum):
    """검색 연산자"""

    AND = "and" # 필수
    OR = "or"  # 선택
    NOT = "not" # 제외

class RetrievalRoute(str, Enum):
    """검색 소스"""

    VECTOR_DB = "vector_book_db" # 국립중앙도서관 도서 벡터 DB
    YONSEI_HOLDINGS = "yonsei_holdings" # 연세대 도서관 소장 자료
    YONSEI_ELECTRONICS = "yonsei_electronics" # 연세대 도서관 전자자료


class LibrarySearchField(str, Enum):
    """검색 필드 타입 (도서관 소장자료 전용)"""

    TOTAL = "TOTAL"  # 전체
    TITLE = "1"  # 서명(책제목)
    AUTHOR = "2"  # 저자
    PUBLISHER = "3"  # 출판사
    SUBJECT = "4"  # 주제어

class HoldingsMaterialType(str, Enum):
    """자료 유형 (도서관 소장자료만)"""

    TOTAL = "TOTAL"  # 전체
    BOOK = "m"  # 단행본
    SERIAL = "s"  # 연속간행물
    MULTIMEDIA = "b;p;v;x;u;c"  # 멀티미디어/비도서
    THESIS = "t"  # 학위논문
    OLD_BOOK = "o"  # 고서
    ARTICLE = "zart"  # 기사

class ElectronicSearchField(str, Enum):
    """검색 필드 타입 (전자자료 전용)"""

    TOTAL = ""      # 전체
    KEYWORD = "TX"  # 키워드
    TITLE = "TI"     # 제목
    AUTHOR = "AU"    # 저자
    SUBJECT = "SU"  # 주제어

class SearchQueries(BaseModel):
    """멀티 쿼리 모델 (최대 3개 쿼리 지원)"""

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
        """쿼리는 순차적으로만 입력 가능: (query_1), (query_1, query_2), (query_1, query_2, query_3)"""

        has_query_2 = bool(self.query_2)
        has_query_3 = bool(self.query_3)
        
        # query_1은 필수이므로 이미 검증됨 (str 타입)
        
        # query_2가 없는데 query_3이 있는 경우 에러
        if not has_query_2 and has_query_3:
            raise ValueError(
                "Invalid query sequence: query_3 cannot exist without query_2. "
                "Valid combinations: (query_1), (query_1, query_2), (query_1, query_2, query_3)"
            )
        
        # query_2가 있으면 search_field_2가 필수
        if has_query_2:
            if self.search_field_2 is None:
                raise ValueError("search_field_2 is required when query_2 is provided")
            
        # query_3이 있으면 operator_2와 search_field_3도 필수
        if has_query_3:
            if self.operator_2 is None:
                raise ValueError("operator_2 is required when query_3 is provided")
            if self.search_field_3 is None:
                raise ValueError("search_field_3 is required when query_3 is provided")
        
        return self


class SearchRequest(BaseModel):
    """
    Strategy Service가 Retrieval Service에 전달하는 구조화된 검색 명세
    """
    
    # 일단 상정한 방법은 아래와 같음 
    queries: SearchQueries = Field(..., description="Multi-query/Step-back/HyDE 등으로 변환된 쿼리들 (최대 3개)")
    routes: List[RetrievalRoute] = Field(
        ...,
        description="검색할 소스들 (도서관 소장, 전자자료, 벡터 DB 등)",
        examples=[
            [RetrievalRoute.VECTOR_DB, RetrievalRoute.YONSEI_HOLDINGS],
            [RetrievalRoute.YONSEI_ELECTRONICS]
        ],
    )
    # 검색 필터 (선택 사항)
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="각 소스별 필터 조건 (연도 범위, 자료 유형 등)",
        examples=[
            # Holdings 용 예시 material_types는 List[HoldingsMaterialType | str]
            {"year_range": (2020, 2023), "material_types": [HoldingsMaterialType.BOOK, HoldingsMaterialType.THESIS]},
            {"year_range": (2023, 2025), "academic_journals_only": False, "foreign_language": False} # Electronic 용 예시
        ]
    )
    # NOTE: 이 top-k가 각 어댑터 각각의 top-k가 되도록 설정되어있는데, 별도로 설정하기는 애매해서 일단 이렇게 둠
    top_k: int = Field(default=10, description="각 소스별 반환 문서 수")
    user_query: str = Field(description="원본 사용자 질문 (CRAG 평가용)")

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

# ================== generation-service 부분 ==================

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