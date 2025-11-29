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

# [New] 검색어 생성기 임포트 (Factory Pattern 적용됨)
from core.generator import QueryTranslationService

# [!] 기존 서비스/모델 임포트 (파일이 없을 경우를 대비한 안전장치)
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

# --- [핵심] Lifespan: 서버 시작 시 모델 로드 ---
translation_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global translation_service
    print("🚀 [System] Strategy Service 시작! LoRA 모델 로드를 시도합니다...")
    
    # 모델 경로 (GitHub 폴더 구조 기준)
    ADAPTER_PATH = "./models/query_translation_adapter_final"
    translation_service = QueryTranslationService(adapter_path=ADAPTER_PATH)
    
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
    [New] 키워드 생성 요청용 (A/B 테스트 및 확장 지원)
    mode: 'openai', 'lora', 'gemini'(예정) 등
    """
    query: str
    mode: str = "openai" # Factory Pattern에 맞춰 구체적인 이름 사용

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Strategy Service (Refactored w/ Factory Pattern) is Running!"}

# 1. 라우팅 엔드포인트
@app.post("/api/v1/strategy/route", response_model=RoutingDecision)
async def route_query(request: QueryRequest, llm_client: OpenAI = Depends(get_llm_client)):
    """사용자 질문을 분석하여 검색 경로(Routing)를 결정합니다."""
    # print(f"▶ 라우팅 요청: {request.query}") # 로그 너무 많으면 주석 처리
    decision = await get_routing_decision(request.query, llm_client)
    return decision

# 2. [New] 키워드 생성 엔드포인트 (A/B Test)
@app.post("/api/v1/strategy/keywords")
async def generate_keywords_api(request: KeywordRequest):
    """
    질문을 받아 검색 키워드를 생성합니다. (확장형 구조 적용)
    - mode='openai': GPT-4o 사용
    - mode='lora': 로컬 T5-LoRA 모델 사용
    - 추후 'gemini', 'upstage' 등 추가 가능
    """
    if translation_service is None:
        raise HTTPException(status_code=500, detail="번역 서비스가 초기화되지 않았습니다.")

    print(f"▶ 키워드 요청 ({request.mode}): {request.query}")
    
    # core/generator.py의 로직 실행 (Factory가 알아서 처리)
    result = translation_service.generate_keywords(request.query, mode=request.mode)
    
    print(f"  ↳ 결과: {result['keywords']} ({result['latency_ms']}ms)")
    return result
