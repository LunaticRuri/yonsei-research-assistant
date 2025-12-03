from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from shared.models import (
    QueryToKeywordRequest,
    RoutingRequestWithQuery,
    RoutingDecision,
    SearchRequest
)
from shared.config import settings

import logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# --- Import Modules ---
# [1] 검색어 생성기 (Factory Pattern)
from strategy_service.core.generator import QueryTranslationService
# [2] 검색 클라이언트 (Retrieval Service 연동)
from strategy_service.core.retrieval_client import RetrievalClient
# [3] 로거 (A/B Test 데이터 수집)
from strategy_service.utils.logger import log_experiment

# --- [핵심] Lifespan: 서버 시작 시 서비스 초기화 ---
translation_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global translation_service
    logger.info("[System] Strategy Service 시작!")
    
    # 키워드 생성기 로드 (LoRA 모델)
    LORA_MODEL_PATH = settings.LORA_MODEL_PATH
    translation_service = QueryTranslationService(adapter_path=LORA_MODEL_PATH)

    yield

    logger.info("[System] Strategy Service 종료.")

app = FastAPI(lifespan=lifespan)


# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Strategy Service is running!"}


# CLI 인터페이스용 실제 동작 엔드포인트 - 이 부분이 맞닿는 부분
# Strategy -> Routing 통합 요청
# Gemini 크레딧이 있어서 CLI는 기본설정을 Gemini로 함
# TODO: 구현해야 함!
@app.post("/cli_stratrgy_request", response_model=SearchRequest)
async def cli_stratrgy_request(request: QueryToKeywordRequest):
    
    if translation_service is None:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")

    # STEP 1: Query -> Keywords
    gen_result = translation_service.generate_keywords(request.query, mode=request.mode)
    keywords_str = gen_result['keywords']
    latency = gen_result['latency_ms']
    
    logger.info(f"생성된 키워드: {keywords_str} ({latency}ms)")

    # (문자열 결과를 리스트로 변환: 쉼표 기준 파싱)
    if isinstance(keywords_str, str):
        # "키워드1, 키워드2" -> ["키워드1", "키워드2"]
        keyword_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
    else:
        keyword_list = []
    
    # STEP 2: Determine Routing
    # NOTE: 이미 구현되어 있는 함수보다 그냥 일단 간이로 작성해서 돌리는게 편할 거 같음!
    # 바람직하지는 않지만, 구현의 편의를 위해 여기에다가 직접 구현.
    
    

    