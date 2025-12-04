from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from shared.models import (
    QueryToKeywordRequest,
    RoutingRequest,
    QueryOperator,
    DefaultSearchField,
    SearchQueries,
    SearchRequest
)
from shared.config import settings

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(settings.console_handler)
logger.addHandler(settings.file_handler)
    

# --- Import Modules ---
# [1] 검색어 생성기 (Factory Pattern)
from strategy_service.core.generator import QueryTranslationService
# [2] 라우터
from strategy_service.core.router import RoutingService

# --- [핵심] Lifespan: 서버 시작 시 서비스 초기화 ---
translation_service = None
routing_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global translation_service, routing_service
    logger.info("[System] Strategy Service 시작!")
    
    # 키워드 생성기 로드 (LoRA 모델)
    LORA_MODEL_PATH = settings.LORA_MODEL_PATH
    translation_service = QueryTranslationService(adapter_path=LORA_MODEL_PATH)

    # 라우팅 서비스 초기화
    routing_service = RoutingService()

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
@app.post("/cli_stratrgy_request", response_model=SearchRequest)
async def cli_stratrgy_request(request: QueryToKeywordRequest):
    
    if translation_service is None or routing_service is None:
        raise HTTPException(status_code=500, detail="서비스가 초기화되지 않았습니다.")

    # STEP 1: Query -> Keywords
    keywords_result = await translation_service.generate_keywords(request.query, mode=request.mode)
    keywords_str = keywords_result['keywords']
    latency = keywords_result['latency_ms']
    
    logger.info(f"Question: {request.query} -> Keywords Generated: {keywords_str} ({latency}ms)")

    # (문자열 결과를 리스트로 변환: 쉼표 기준 파싱)
    if isinstance(keywords_str, str):
        # "키워드1, 키워드2" -> ["키워드1", "키워드2"]
        keyword_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
    else:
        keyword_list = []
    
    # STEP 2: Determine Routing
    # NOTE: 이미 구현되어 있는 함수보다 그냥 일단 간이로 작성해서 돌리는게 편할 거 같음!
    routing_request = RoutingRequest(
        query=request.query,
        keywords=keyword_list
    )
    routing_decision = await routing_service.determine_routing(routing_request)
    logger.info(f"Routing -> {routing_decision.routes}")

    # STEP 3: Construct SearchRequest

    if len(keyword_list) > 3:
        keyword_list = keyword_list[:3]  # 최대 3개 키워드로 제한
    
    # 키워드 수에 따라 SearchQueries 구성
    search_queries = None
    
    if len(keyword_list) == 1:
        search_queries = SearchQueries(
            query_1=keyword_list[0],
            search_field_1=DefaultSearchField.TOTAL
        )
    elif len(keyword_list) == 2:
        search_queries = SearchQueries(
            query_1=keyword_list[0],
            search_field_1=DefaultSearchField.TOTAL,
        operator_1=QueryOperator.AND,
            query_2=keyword_list[1],
            search_field_2=DefaultSearchField.TOTAL
        )
    elif len(keyword_list) == 3:
        search_queries = SearchQueries(
            query_1=keyword_list[0],
            search_field_1=DefaultSearchField.TOTAL,
            operator_1=QueryOperator.AND,
            query_2=keyword_list[1],
            search_field_2=DefaultSearchField.TOTAL,
            operator_2=QueryOperator.AND,
            query_3=keyword_list[2],
            search_field_3=DefaultSearchField.TOTAL
        )
    else:
        # 키워드가 없을 경우 원본 쿼리를 사용
        search_queries = SearchQueries(
            query_1=request.query,
            search_field_1=DefaultSearchField.TOTAL
        )
    
    search_request = SearchRequest(
        queries=search_queries,
        routes=routing_decision.routes,
        top_k=10,
        user_query=request.query
    )
    
    logger.debug(f"Constructed SearchRequest: {search_request}")

    # 최종 SearchRequest 반환
    return search_request

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)