from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import sys
from dotenv import load_dotenv
from contextlib import asynccontextmanager # [New] 서버 시작/종료 이벤트 처리용

# [!] 경로 설정 (기존 유지)
sys.path.append(os.path.abspath('services'))
sys.path.append(os.path.abspath('../shared'))
sys.path.append(os.path.abspath('..'))

# .env 로드
try:
    load_dotenv(dotenv_path='../.env')
except Exception as e:
    print(f"[경고] .env 파일 로드 실패 (무시하고 진행): {e}")

# [New] 우리가 만든 검색어 생성기 임포트
from core.generator import QueryTranslationService
# 기존 라우팅 서비스 임포트
from services.routing_service import get_routing_decision
from shared.models import RoutingDecision

# --- [핵심] Lifespan(수명주기) 설정: 서버 켤 때 모델 로딩 ---
translation_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 서버 시작 시 실행: 모델 로드
    global translation_service
    print("🚀 [System] Strategy Service 시작! LoRA 모델을 로드합니다...")
    
    # 모델 경로 (GitHub 구조에 맞춤)
    ADAPTER_PATH = "./models/query_translation_adapter_final"
    translation_service = QueryTranslationService(adapter_path=ADAPTER_PATH)
    
    yield # 여기서부터 서버가 실제 동작함
    
    # 2. 서버 종료 시 실행 (필요하면 정리 작업)
    print("👋 [System] Strategy Service 종료.")

# 앱 생성 (lifespan 적용)
app = FastAPI(lifespan=lifespan)

# --- 의존성 주입 ---
def get_llm_client():
    try:
        return OpenAI() # 환경변수 OPENAI_API_KEY 사용
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI 클라이언트 에러: {e}")

# --- DTO (데이터 전송 객체) 정의 ---

class QueryRequest(BaseModel):
    """기존 라우팅 요청용"""
    query: str

class KeywordRequest(BaseModel):
    """[New] 키워드 생성 요청용 (A/B 테스트 지원)"""
    query: str
    mode: str = "api" # 기본값은 api ("api" or "lora")

# --- API 엔드포인트 ---

@app.get("/")
def read_root():
    return {"message": "Strategy Service (Routing & Query Translation) is Running!"}

# 1. 라우팅 엔드포인트 (기존)
@app.post("/api/v1/strategy/route", response_model=RoutingDecision)
async def route_query(
    request: QueryRequest,
    llm_client: OpenAI = Depends(get_llm_client)
):
    print(f"▶ 라우팅 요청: {request.query}")
    decision = await get_routing_decision(request.query, llm_client)
    print(f"  ↳ 결정: {decision.route}")
    return decision

# 2. [New] 키워드 생성 엔드포인트 (A/B 테스트용)
@app.post("/api/v1/strategy/keywords")
async def generate_keywords_api(request: KeywordRequest):
    """
    질문을 받아 검색 키워드를 생성합니다.
    mode='api': GPT-4o 사용
    mode='lora': 로컬 T5-LoRA 모델 사용
    """
    print(f"▶ 키워드 생성 요청 ({request.mode}): {request.query}")
    
    if translation_service is None:
        raise HTTPException(status_code=500, detail="번역 서비스가 초기화되지 않았습니다.")

    # core/generator.py의 로직 실행
    result = translation_service.generate_keywords(request.query, mode=request.mode)
    
    print(f"  ↳ 결과: {result['keywords']} ({result['latency_ms']}ms)")
    return result