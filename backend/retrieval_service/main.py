from fastapi import FastAPI, HTTPException
from shared.models import SearchRequest, GenerationRequest
from retrieval_service.services.search_executor import SearchExecutor
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Retrieval Service", version="1.0.0")

service = SearchExecutor()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/search", response_model=GenerationRequest)
async def search(request: SearchRequest):
    """
    전체 검색 파이프라인 실행 엔드포인트
    """
    try:
        logger.info(f"Generating response for query: {request.query}")
        result = await service.execute(request)
        return result
    except Exception as e:
        logger.error(f"Error in generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
