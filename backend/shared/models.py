from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# ===== 기본 모델들 =====
# ( ... 생략 ... )
# (GitHub에 있던 다른 모델들은 그대로 둡니다)

class DialogueRequest(BaseModel):
    """소크라테스식 대화 요청"""
    session_id: str
    message: str
    conversation_history: Optional[List[str]] = []

# ( ... 수많은 다른 모델들 ... )

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
# 1. Pydantic 모델 정의 (TypeScript의 인터페이스 역할)
class Conversation(BaseModel):
    id: str  # 각 대화의 고유 ID (라우팅에 사용)
    title: str
    last_updated: str

# ===== 라우팅 =====
# [!] 충돌 해결:
# 우리가 테스트한 'RoutingDecision' 모델 (213c214)을 선택하고,
# 충돌이 발생한 'RouteRequest' (HEAD)와 
# 그 짝이었던 'RouteResponse' (HEAD)는 제거합니다.

class RoutingDecision(BaseModel):
    """라우팅 결정 결과를 담는 모델"""
    route: str = Field(..., description="라우팅 경로 (e.g., 'rag_service', 'search_agent_service')")
    reason: str = Field(..., description="라우팅 결정 이유")

# (기존 RouteResponse 모델은 여기서 삭제됨)


# ===== 도서관 소장 정보 =====
class LibraryHoldingInfo(BaseModel):
    """도서관 소장 자료 상세 정보"""
    access_id: str = Field(..., description="자료 접근 ID (CATTOT...)")  
    title: str = Field(default="", description="자료 제목")
    author: str = Field(default="", description="저자")
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
