import logging
from fastapi import FastAPI, HTTPException
from shared.models import StrategyGenerationRequest, StrategyUpdateRequest, SearchStrategyResponse
from services.strategy_engine import StrategyEngine
from services.keyword_analyzer import KeywordAnalyzer

# --- [추가] 로깅 시스템 설정 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("strategy_service.log"), # 파일에 로그 저장
        logging.StreamHandler() # 터미널에 로그 출력
    ]
)
logger = logging.getLogger(__name__)
# --------------------------------

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
    logger.info("Health check requested.")
    return {"status": "healthy", "service": "strategy-service"}

@app.post("/generate", response_model=SearchStrategyResponse)
async def generate_strategy(request: StrategyGenerationRequest):
    """대화 내용을 바탕으로 초기 검색 전략 생성"""
    try:
        logger.info(f"Generating strategy for session_id: {request.session_id}")
        strategy_response = await strategy_engine.generate_initial_strategy(
            session_id=request.session_id,
            study_summary=request.study_summary,
            research_topic=request.research_topic,
            key_concepts=request.key_concepts
        )
        logger.info(f"Successfully generated strategy for session_id: {request.session_id}")
        return strategy_response
    
    # --- [변경] 표준 에러 처리 로직 ---
    except Exception as e:
        # exc_info=True를 통해 에러의 상세 내용(traceback)을 로그에 기록
        logger.error(f"Strategy generation failed for session_id: {request.session_id}", exc_info=True)
        # 사용자에게는 표준화된 JSON 에러 메시지를 반환
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "STRATEGY_GENERATION_FAILED",
                "message": f"전략 생성 중 예상치 못한 오류가 발생했습니다: {e}"
            }
        )
    # --------------------------------

@app.post("/update", response_model=SearchStrategyResponse)
async def update_strategy(request: StrategyUpdateRequest):
    # (이 부분의 에러 처리도 위와 동일한 방식으로 개선할 수 있습니다)
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
        logger.error(f"Strategy update failed for session_id: {request.session_id}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "STRATEGY_UPDATE_FAILED",
                "message": f"전략 업데이트 중 예상치 못한 오류가 발생했습니다: {e}"
            }
        )

@app.get("/validate/{session_id}")
async def validate_strategy(session_id: str):
    """현재 전략의 유효성 검증"""
    try:
        logger.info(f"Validating strategy for session_id: {session_id}")
        validation_result = await strategy_engine.validate_strategy(session_id)
        return validation_result

    except Exception as e:
        logger.error(f"Strategy validation failed for session_id: {session_id}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "STRATEGY_VALIDATION_FAILED",
                "message": f"전략 검증 중 예상치 못한 오류가 발생했습니다: {e}"
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)