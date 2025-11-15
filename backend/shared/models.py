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
