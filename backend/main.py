from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from shared.models import *
from shared.config import settings

# https://github.com/faulander/fastapi-sveltekit-template 로그인/회원가입 코드 이쪽에 있으니 참고하셔서 구현하시면 좋을 것 같습니다!

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

# ==== 대화 목록 =====
# 임시 데이터베이스 (실제 DB로 대체해야 합니다)
# user_id에 따라 연구 목록이 다릅니다.
FAKE_STUDIES_DB = {
    "user123": [
        {"id": "c001", "title": "SvelteKit 프로젝트 시작", "last_updated": "2025-10-01T10:00:00Z"},
        {"id": "c002", "title": "FastAPI 인증 구현 질문", "last_updated": "2025-10-02T11:30:00Z"},
    ],
    "user456": [
        {"id": "c003", "title": "새로운 기능 아이디어", "last_updated": "2025-10-03T12:00:00Z"},
    ],
}

# 새로운 연구 추가 엔드포인트
@app.post("/api/studies/new", response_model=List[Conversation])
async def create_study(user_id: str):
    """
    새로운 연구를 추가합니다.
    """ 
    if user_id not in FAKE_STUDIES_DB:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_study = {
        "id": f"c00{len(FAKE_STUDIES_DB[user_id]) + 1}",
        "title": "연구" + str(len(FAKE_STUDIES_DB[user_id]) + 1),
        "last_updated": datetime.now().isoformat()
    }
    FAKE_STUDIES_DB[user_id].append(new_study)
    return new_study

# 1. 대화 목록을 불러오는 엔드포인트
@app.get("/api/studies", response_model=List[Conversation])
async def get_studies(user_id: str):
    """
    현재 로그인된 사용자(user_id)의 모든 대화 목록을 반환합니다.
    실제로는 인증 토큰에서 user_id를 추출해야 합니다.
    """
    if user_id not in FAKE_STUDIES_DB:
        # 사용자가 없을 경우 빈 목록 반환 또는 404
        return []

    return FAKE_STUDIES_DB.get(user_id, [])

# 2. 특정 연구의 상세 내용을 불러오는 엔드포인트
@app.get("/api/studies/{study_id}")
async def get_study_details(study_id: str, user_id: str):
    """
    특정 연구 ID와 사용자 ID에 해당하는 연구 내용을 반환합니다.
    """
    # 보안: 요청된 대화 ID가 해당 user_id 소유인지 확인해야 합니다.
    
    # 임시 검증 로직 (실제 DB에서는 쿼리로 처리)
    user_studies = FAKE_STUDIES_DB.get(user_id, [])
    study = next((c for c in user_studies if c['id'] == study_id), None)

    if not study:
        raise HTTPException(status_code=404, detail="Study not found or access denied")

    # 대화 메시지 등의 상세 데이터 추가 (임시)
    return {
        "id": study_id,
        "title": study['title'],
        "messages1": [
            {"role": "user", "text": "첫 번째 질문입니다(1)."},
            {"role": "assistant", "text": "첫 번째 응답입니다(1)."},
        ],
        "messages1_complete": False,

        "messages2": [
            {"role": "user", "text": "첫 번째 질문입니다(2)."},
            {"role": "assistant", "text": "첫 번째 응답입니다(2)."},
        ],
        "messages2_complete": False,
        
        "messages3": [
            {"role": "user", "text": "첫 번째 질문입니다(3)."},
            {"role": "assistant", "text": "첫 번째 응답입니다(3)."},
        ],
        "messages3_complete": False
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)