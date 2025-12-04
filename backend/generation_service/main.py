from fastapi import FastAPI, HTTPException
from shared.models import GenerationRequest, GenerationResult
from generation_service.services.generator import GeneratorService
from shared.config import settings
import logging

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(settings.console_handler)
logger.addHandler(settings.file_handler)

app = FastAPI(title="Generation Service", version="1.0.0")

generator_service = GeneratorService()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/generate", response_model=GenerationResult)
async def generate_response(request: GenerationRequest):
    """
    Generate a response based on the retrieval result using Self-RAG.
    """
    try:
        logger.info(f"Generating response for query: {request.query}")
        # TODO: Self-RAG 비활성화한 경우와 비교
        # result = await generator_service.generate_without_self_rag(request.query, request.retrieval_result) 
        result = await generator_service.generate(request.query, request.retrieval_result)
        return result
    except Exception as e:
        logger.error(f"Error in generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
