from fastapi import FastAPI, HTTPException
from shared.models import LibrarySearchRequest, LibrarySearchResponse, DocumentResult
from .services.library_scraper import LibraryScraper
from .services.search_executor import SearchExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Search Agent Service",
    description="연세대학교 도서관 검색 에이전트 서비스",
    version="1.0.0"
)

# 서비스 초기화
library_scraper = LibraryScraper()
search_executor = SearchExecutor(library_scraper)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "search-agent-service"}

@app.post("/execute", response_model=LibrarySearchResponse)
async def execute_library_search(request: LibrarySearchRequest):
    """도서관 검색 실행"""
    try:
        search_result = await search_executor.execute_search(
            search_strategy=request.search_strategy,
            session_id=request.session_id,
            max_results=request.max_results or 20
        )
        return search_result
    
    except Exception as e:
        logger.error(f"Library search error: {e}")
        raise HTTPException(status_code=500, detail="도서관 검색 중 오류가 발생했습니다.")

@app.get("/document/{code}", response_model=DocumentResult)
async def fetch_document(code: str):
    """특정 문서의 메타데이터 확인"""
    try:
        result = await library_scraper.fetch_document(code)
        if not result:
            raise HTTPException(status_code=404, detail="자료를 찾을 수 없습니다.")
        return result
    
    except Exception as e:
        logger.error(f"Availability check error: {e}")
        raise HTTPException(status_code=500, detail="소장 여부 확인 중 오류가 발생했습니다.")

@app.get("/test-connection")
async def test_library_connection():
    """도서관 웹사이트 연결 테스트"""
    try:
        connection_status = await library_scraper.test_connection()
        return connection_status
    
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)