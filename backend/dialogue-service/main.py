# ==== PATH DIAG + FIX (put this at VERY TOP) ====
import sys, os
from pathlib import Path

HERE = Path(__file__).resolve()                 # .../backend/dialogue-service/main.py
BACKEND_DIR = HERE.parents[1]                   # .../backend
ROOT_DIR = HERE.parents[2] if len(HERE.parents) >= 2 else None  # .../ (프로젝트 루트)

def _ensure_path(p: Path):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

# 1) shared가 있는 'backend'를 우선 경로에 추가
_ensure_path(BACKEND_DIR)

# (선택) 2) 루트도 추가해 패키지 실행 방식 바뀌어도 안전하게
if ROOT_DIR:
    _ensure_path(ROOT_DIR)

# 디버그: 실제 탐색 경로와 shared 존재 여부 출력
print("[DEBUG] sys.path[0:3] =", sys.path[:3])
print("[DEBUG] BACKEND_DIR =", BACKEND_DIR)
print("[DEBUG] shared exists? ", (BACKEND_DIR / "shared").exists())
print("[DEBUG] models.py exists? ", (BACKEND_DIR / "shared" / "models.py").exists())
# ===============================================

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
