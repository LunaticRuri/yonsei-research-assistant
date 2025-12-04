from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from shared.models import SearchRequest, GenerationRequest
from retrieval_service.services.search_executor import SearchExecutor
from shared.config import settings
import logging

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(settings.console_handler)
logger.addHandler(settings.file_handler)

app = FastAPI(title="Retrieval Service", version="1.0.0")

service = SearchExecutor()

# Debugging: 요청 유효성 검사 오류 처리기
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()}")
    logger.error(f"Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/search", response_model=GenerationRequest)
async def search(request: SearchRequest):
    """
    전체 검색 파이프라인 실행 엔드포인트
    """
    try:
        logger.info(f"Generating response for query: {request.user_query}")
        result = await service.execute(request)
        return result
    except Exception as e:
        logger.error(f"Error in generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
