from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import sys
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# [!] 경로 설정 (어디서 실행하든 현재 파일 위치 기준으로 경로 잡기)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.abspath(os.path.join(current_dir, 'services')))
sys.path.append(os.path.abspath(os.path.join(current_dir, '../shared')))
sys.path.append(os.path.abspath(os.path.join(current_dir, '..')))

# .env 로드
try:
    load_dotenv(dotenv_path='../.env')
except Exception as e:
    print(f"[경고] .env 파일 로드 실패: {e}")

# --- Import Modules ---
# [1] 검색어 생성기 (Factory Pattern)
from core.generator import QueryTranslationService
# [2] 검색 클라이언트 (Retrieval Service 연동)
from core.retrieval_client import RetrievalClient
# [3] 로거 (A/B Test 데이터 수집)
from utils.logger import log_experiment

# [!] 기존 서비스/모델 임포트 (안전장치)
try:
    from services.routing_service import get_routing_decision
    from shared.models import RoutingDecision
except ImportError:
    print("⚠️ [Warning] 라우팅 서비스 파일을 찾을 수 없습니다. Mock 객체를 사용합니다.")
    class RoutingDecision(BaseModel):
        route: str = "search-agent"
        reason: str = "Import Error Mock"
    async def get_routing_decision(q, c):
        return RoutingDecision()

# --- [핵심] Lifespan: 서버 시작 시 서비스 초기화 ---
translation_service = None
retrieval_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global translation_service, retrieval_client
    print("🚀 [System] Strategy Service 시작!")
    
    # 1. 키워드 생성기 로드 (LoRA 모델)
    ADAPTER_PATH = "./models/query_translation_adapter_final"
    translation_service = QueryTranslationService(adapter_path=ADAPTER_PATH)
    
    # 2. 검색 클라이언트 초기화
    retrieval_client = RetrievalClient()
    
    yield
    print("👋 [System] Strategy Service 종료.")

app = FastAPI(lifespan=lifespan)

# --- 의존성 주입 ---
def get_llm_client():
    try:
        return OpenAI()
    except:
        return None

# --- DTO Definition ---

class QueryRequest(BaseModel):
    """기존 라우팅 요청용"""
    query: str

class KeywordRequest(BaseModel):
    """
    [New] 통합 검색 요청용 (A/B 테스트 및 확장 지원)
    mode: 'openai', 'lora', 'gemini'(예정) 등
    """
    query: str
    mode: str = "openai" # Factory Pattern에 맞춰 구체적인 이름 사용

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Strategy Service (Full Pipeline: Gen -> Log -> Search) is Running!"}

# 1. 라우팅 엔드포인트
@app.post("/api/v1/strategy/route", response_model=RoutingDecision)
async def route_query(request: QueryRequest, llm_client: OpenAI = Depends(get_llm_client)):
    """사용자 질문을 분석하여 검색 경로(Routing)를 결정합니다."""
    decision = await get_routing_decision(request.query, llm_client)
    return decision

# 2. [New] 통합 검색 엔드포인트 (키워드 생성 + 검색 + 로그)
@app.post("/api/v1/strategy/keywords")
async def generate_keywords_and_search(request: KeywordRequest):
    """
    전체 파이프라인 실행:
    1. 키워드 생성 (Strategy)
    2. 로그 기록 (A/B Test 데이터 수집)
    3. 검색 요청 (Retrieval Service 호출) -> 최종 결과 반환
    """
    if translation_service is None or retrieval_client is None:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")

    print(f"\n▶ [Step 1] 키워드 생성 요청 ({request.mode}): {request.query}")
    
    # 1. 키워드 생성 (Strategy Service)
    gen_result = translation_service.generate_keywords(request.query, mode=request.mode)
    keywords_str = gen_result['keywords']
    latency = gen_result['latency_ms']
    
    print(f"   ↳ 생성된 키워드: {keywords_str} ({latency}ms)")

    # (문자열 결과를 리스트로 변환: 쉼표 기준 파싱)
    if isinstance(keywords_str, str):
        # "키워드1, 키워드2" -> ["키워드1", "키워드2"]
        keyword_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
    else:
        keyword_list = []

    # 2. 로그 기록 (A/B Test)
    # (주의: 파일 I/O 에러가 나도 전체 서비스는 안 죽게 내부에서 try-except 처리됨)
    log_experiment(request.query, request.mode, keyword_list, latency)

    # 3. 검색 서비스 호출 (Retrieval Service)
    print(f"▶ [Step 2] 검색 서비스 호출 (Keywords: {keyword_list})")
    
    # 실제 검색 수행 (비동기 호출)
    search_result = await retrieval_client.request_search(request.query, keyword_list)
    
    # 4. 최종 결과 반환
    return {
        "query": request.query,
        "strategy_result": gen_result, # 키워드 생성 결과
        "retrieval_result": search_result # 실제 검색 결과 (논문 등)
    }
