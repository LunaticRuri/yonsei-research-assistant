from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

# [!] 우리가 만든 모듈/모델 임포트
#     (Colab 테스트 환경을 가정하여, sys.path를 직접 설정)
import sys
sys.path.append(os.path.abspath('services')) # 'services' 폴더 경로 추가
sys.path.append(os.path.abspath('../shared')) # 'shared' 폴더 경로 추가
sys.path.append(os.path.abspath('..')) # 'backend' 폴더 경로 추가 (shared를 찾기 위함)

# [!] 중요: .env 파일을 FastAPI 시작 시 로드
#     (실제 서버에서는 uvicorn 실행 위치에 따라 경로 조정 필요)
try:
    load_dotenv(dotenv_path='../.env') # .env 파일이 backend 폴더에 있다고 가정
except Exception as e:
    print(f"[경고] .env 파일 로드 실패 (무시하고 진행): {e}")


from services.routing_service import get_routing_decision
from shared.models import RoutingDecision

# --- FastAPI 앱 및 클라이언트 설정 ---

app = FastAPI()

# [!] (임시) OpenAI 클라이언트를 의존성으로 주입하는 함수
#     (실제로는 config.py나 llm_factory.py에서 가져오겠죠!)
def get_llm_client():
    try:
        client = OpenAI()
        yield client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI 클라이언트 생성 실패: {e}")

# --- API 엔드포인트 정의 ---

class QueryRequest(BaseModel):
    """라우팅 요청을 위한 Pydantic 모델"""
    query: str

@app.post("/api/v1/strategy/route", response_model=RoutingDecision)
async def route_query(
    request: QueryRequest,
    llm_client: OpenAI = Depends(get_llm_client) # 의존성 주입
):
    """
    사용자 질문(query)을 받아 적절한 서비스(RAG 또는 웹 검색)로 라우팅합니다.
    """
    print(f"▶ 라우팅 요청 수신: {request.query}")
    
    # [!] 1단계에서 완성한 서비스 함수를 그대로 호출!
    decision = await get_routing_decision(request.query, llm_client)
    
    # [!] (향후 확장)
    # 여기서 decision.route 값에 따라 
    # httpx 같은 클라이언트로 rag_service나
    # search_agent_service에 실제 요청을 보낼 수 있습니다.
    
    print(f"  - 결정된 경로: {decision.route}")
    return decision

@app.get("/")
def read_root():
    return {"message": "Strategy Service (라우팅/전략) API입니다."}