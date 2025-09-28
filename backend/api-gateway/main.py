from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from shared.models import *
from shared.config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Yonsei Research Assistant API Gateway",
    description="수리조교 - 연세대학교 학술 연구 보조 AI의 중앙 API Gateway",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 프론트엔드 URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 URL 매핑
SERVICES = {
    "dialogue": "http://localhost:8001",
    "strategy": "http://localhost:8002", 
    "rag": "http://localhost:8003",
    "search_agent": "http://localhost:8004"
}

async def forward_request(service_name: str, endpoint: str, method: str = "POST", data: dict = None):
    """다른 마이크로서비스로 요청을 전달하는 헬퍼 함수"""
    service_url = SERVICES.get(service_name)
    if not service_url:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    url = f"{service_url}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        if method == "POST":
            response = await client.post(url, json=data)
        else:
            response = await client.get(url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return response.json()

@app.get("/")
async def root():
    return {"message": "Yonsei Research Assistant API Gateway"}

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "services": list(SERVICES.keys())}

# 1단계: 소크라테스식 대화
@app.post("/api/dialogue", response_model=DialogueResponse)
async def handle_dialogue(request: DialogueRequest):
    """대화 서비스로 요청 전달"""
    return await forward_request("dialogue", "/dialogue", "POST", request.dict())

# 2단계: 검색 전략 생성
@app.post("/api/strategy/generate", response_model=SearchStrategyResponse)
async def generate_strategy(request: StrategyGenerationRequest):
    """전략 서비스로 요청 전달"""
    return await forward_request("strategy", "/generate", "POST", request.dict())

@app.post("/api/strategy/update", response_model=SearchStrategyResponse)
async def update_strategy(request: StrategyUpdateRequest):
    """전략 업데이트 요청 전달"""
    return await forward_request("strategy", "/update", "POST", request.dict())

# 3단계: RAG 분석
@app.post("/api/rag/analyze", response_model=RAGAnalysisResponse)
async def analyze_with_rag(request: RAGAnalysisRequest):
    """RAG 서비스로 분석 요청 전달"""
    return await forward_request("rag", "/analyze", "POST", request.dict())

# 4단계: 도서관 검색
@app.post("/api/search/execute", response_model=LibrarySearchResponse)
async def execute_library_search(request: LibrarySearchRequest):
    """검색 에이전트 서비스로 요청 전달"""
    return await forward_request("search_agent", "/execute", "POST", request.dict())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)