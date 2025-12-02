from fastapi import FastAPI, HTTPException
from shared.models import GenerationRequest, GenerationResult
from generation_service.services.generator import GeneratorService
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        result = await generator_service.generate(request.query, request.retrieval_result)
        return result
    except Exception as e:
        logger.error(f"Error in generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
