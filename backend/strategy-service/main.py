from fastapi import FastAPI, HTTPException
from shared.models import StrategyGenerationRequest, StrategyUpdateRequest, SearchStrategyResponse
from .services.strategy_engine import StrategyEngine
from .services.keyword_analyzer import KeywordAnalyzer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Strategy Service",
    description="검색 전략 생성 및 관리 서비스",
    version="1.0.0"
)

# 서비스 초기화
keyword_analyzer = KeywordAnalyzer()
strategy_engine = StrategyEngine(keyword_analyzer)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "strategy-service"}

@app.post("/generate", response_model=SearchStrategyResponse)
async def generate_strategy(request: StrategyGenerationRequest):
    """대화 내용을 바탕으로 초기 검색 전략 생성"""
    try:
        strategy = await strategy_engine.generate_initial_strategy(
            session_id=request.session_id,
            conversation_summary=request.conversation_summary,
            research_topic=request.research_topic,
            key_concepts=request.key_concepts
        )
        return strategy
    
    except Exception as e:
        logger.error(f"Strategy generation error: {e}")
        raise HTTPException(status_code=500, detail="전략 생성 중 오류가 발생했습니다.")

@app.post("/update", response_model=SearchStrategyResponse)
async def update_strategy(request: StrategyUpdateRequest):
    """사용자 피드백을 바탕으로 검색 전략 업데이트"""
    try:
        updated_strategy = await strategy_engine.update_strategy(
            session_id=request.session_id,
            current_strategy=request.current_strategy,
            user_modifications=request.modifications,
            feedback=request.feedback
        )
        return updated_strategy
    
    except Exception as e:
        logger.error(f"Strategy update error: {e}")
        raise HTTPException(status_code=500, detail="전략 업데이트 중 오류가 발생했습니다.")

@app.get("/validate/{session_id}")
async def validate_strategy(session_id: str):
    """현재 전략의 유효성 검증"""
    try:
        validation_result = await strategy_engine.validate_strategy(session_id)
        return validation_result
    
    except Exception as e:
        logger.error(f"Strategy validation error: {e}")
        raise HTTPException(status_code=500, detail="전략 검증 중 오류가 발생했습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)