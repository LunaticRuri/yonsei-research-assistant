import sys
import os

from fastapi import FastAPI
from shared.models import DialogueRequest, DialogueResponse
from services.dialogue_engine import DialogueEngine
from services.llm_client import LLMClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dialogue Service",
    description="소크라테스식 대화를 통한 연구 주제 구체화 서비스",
    version="1.0.0"
)

# 서비스 초기화
llm_client = LLMClient()
dialogue_engine = DialogueEngine(llm_client)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dialogue-service"}

@app.post("/dialogue", response_model=DialogueResponse)
async def handle_dialogue(request: DialogueRequest):
    """소크라테스식 대화 처리"""
    try:
        response = await dialogue_engine.process_dialogue(
            session_id=request.session_id,
            user_message=request.message,
            conversation_history=request.conversation_history
        )
        return response
    
    except Exception as e:
        logger.error(f"Dialogue processing error: {e}")
        return DialogueResponse(
            session_id=request.session_id,
            response_text="죄송합니다. 처리 중 오류가 발생했습니다. 다시 시도해 주세요.",
            conversation_stage=1,
            follow_up_questions=[],
            insights=[]
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
