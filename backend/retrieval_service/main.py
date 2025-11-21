from fastapi import FastAPI, HTTPException
from shared.models import SearchRequest, RetrievalResult
import logging

from retrieval_service.services.search_executor import SearchExecutor
from retrieval_service.config import settings

# 로깅 설정
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Retrieval Service",
    description="Multi-source document retrieval for Yonsei Research Assistant",
    version="1.0.0"
)

# 서비스 초기화
executor = SearchExecutor()

@app.post("/search", response_model=RetrievalResult)
async def search(request: SearchRequest):
    """
    메인 검색 엔드포인트
    
    Strategy Service로부터 받은 요청 처리:
    - Multi-query 검색
    - Rerank + Fusion
    - CRAG 품질 평가
    """
    try:
        logger.info(f"Received search request: {request.queries[:2]}...")
        result = await executor.execute(request)
        return result
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    서비스 및 데이터 소스 상태 확인
    """
    try:
        adapter_status = await executor.retriever.health_check()
        
        all_healthy = all(adapter_status.values())
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "adapters": adapter_status,
            "service": settings.SERVICE_NAME
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "endpoints": ["/search", "/health"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )