from fastapi import FastAPI, HTTPException
from shared.models import RAGAnalysisRequest, RAGAnalysisResponse
from .services.rag_engine import RAGEngine
from .services.vector_store import VectorStoreManager
from .services.document_processor import DocumentProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG Service",
    description="검색 증강 생성을 통한 학술 문헌 분석 서비스",
    version="1.0.0"
)

# 서비스 초기화
vector_store = VectorStoreManager()
document_processor = DocumentProcessor()
rag_engine = RAGEngine(vector_store, document_processor)

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 벡터 저장소 초기화"""
    try:
        await vector_store.initialize()
        logger.info("Vector store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rag-service"}

@app.post("/analyze", response_model=RAGAnalysisResponse)
async def analyze_with_rag(request: RAGAnalysisRequest):
    """RAG를 사용한 문헌 분석"""
    try:
        analysis_result = await rag_engine.analyze_documents(
            search_strategy=request.search_strategy,
            session_id=request.session_id,
            analysis_depth=request.analysis_depth or "standard"
        )
        return analysis_result
    
    except Exception as e:
        logger.error(f"RAG analysis error: {e}")
        raise HTTPException(status_code=500, detail="RAG 분석 중 오류가 발생했습니다.")

@app.post("/ingest")
async def ingest_documents(documents: list):
    """새로운 문서들을 벡터 저장소에 추가"""
    try:
        result = await rag_engine.ingest_documents(documents)
        return {"message": f"Successfully ingested {result['count']} documents"}
    
    except Exception as e:
        logger.error(f"Document ingestion error: {e}")
        raise HTTPException(status_code=500, detail="문서 수집 중 오류가 발생했습니다.")

@app.get("/collection/status")
async def get_collection_status():
    """벡터 컬렉션 상태 조회"""
    try:
        status = await vector_store.get_collection_status()
        return status
    
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="상태 조회 중 오류가 발생했습니다.")

@app.post("/search/similar")
async def search_similar_documents(query: str, limit: int = 10):
    """유사 문서 검색"""
    try:
        similar_docs = await vector_store.similarity_search(query, limit)
        return {"documents": similar_docs}
    
    except Exception as e:
        logger.error(f"Similarity search error: {e}")
        raise HTTPException(status_code=500, detail="유사 문서 검색 중 오류가 발생했습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)