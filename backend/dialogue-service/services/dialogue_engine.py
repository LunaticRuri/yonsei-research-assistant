from typing import List, Optional
from shared.models import DialogueResponse
from .llm_client import LLMClient
from .prompts import DialoguePrompts
import uuid

class DialogueEngine:
    """소크라테스식 대화를 관리하는 엔진"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.prompts = DialoguePrompts()
        self.sessions = {}  # 세션 상태 관리
    
    async def process_dialogue(
        self, 
        session_id: str, 
        user_message: str, 
        conversation_history: Optional[List[str]] = None
    ) -> DialogueResponse:
        """대화 처리 메인 로직"""
        
        # 세션 초기화
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "stage": 1,  # 대화 단계
                "topic_clarity": 0,  # 주제 명확도 (1-10)
                "key_concepts": [],  # 추출된 핵심 개념들
                "research_direction": None  # 연구 방향성
            }
        
        session = self.sessions[session_id]
        
        # 현재 단계에 따른 프롬프트 생성
        prompt = self.prompts.get_dialogue_prompt(
            stage=session["stage"],
            user_message=user_message,
            conversation_history=conversation_history or [],
            session_context=session
        )
        
        # LLM을 통한 응답 생성
        llm_response = await self.llm_client.generate_response(prompt)  #llm_client.generate_structured_response 로 변경 필요
        
        # 응답 파싱 및 세션 업데이트
        parsed_response = self._parse_llm_response(llm_response)
        self._update_session_state(session_id, parsed_response, user_message)
        
        return DialogueResponse(
            session_id=session_id,
            response_text=parsed_response["response"],
            conversation_stage=session["stage"],
            follow_up_questions=parsed_response.get("follow_ups", []),
            insights=parsed_response.get("insights", []),
            topic_clarity_score=session["topic_clarity"]
        )
    
    def _parse_llm_response(self, llm_response: str) -> dict:
        """LLM 응답을 구조화된 데이터로 파싱"""
        # TODO: JSON 응답 파싱 로직 구현
        # LLM에게 JSON 형식으로 응답하도록 요청하고 파싱
        return {
            "response": llm_response,
            "follow_ups": [],
            "insights": []
        }
    
    def _update_session_state(self, session_id: str, parsed_response: dict, user_message: str):
        """세션 상태 업데이트"""
        session = self.sessions[session_id]
        
        # 주제 명확도 평가
        session["topic_clarity"] = self._evaluate_topic_clarity(user_message, parsed_response)
        
        # 대화 단계 진행 판단
        if session["topic_clarity"] >= 7:  # 충분히 명확해지면 다음 단계로
            session["stage"] = min(session["stage"] + 1, 4)
    
    def _evaluate_topic_clarity(self, user_message: str, parsed_response: dict) -> int:
        """주제 명확도 평가 (1-10)"""
        # TODO: 실제 명확도 평가 로직 구현
        # 키워드 수, 구체성, 연구 가능성 등을 평가
        return 5
    
    def get_session_summary(self, session_id: str) -> dict:
        """세션 요약 정보 반환"""
        return self.sessions.get(session_id, {})
    
    def is_ready_for_strategy(self, session_id: str) -> bool:
        """전략 수립 단계로 진행 가능한지 확인"""
        session = self.sessions.get(session_id, {})
        return session.get("topic_clarity", 0) >= 7
