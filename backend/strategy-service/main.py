# /backend/strategy-service/main.py

from fastapi import FastAPI, HTTPException, Depends
from openai import OpenAI
import json
import sys
import os
from typing import Dict

# --- 1. 'shared' 모듈 경로 설정 ---
# Colab/로컬 환경 모두에서 shared 폴더를 찾도록 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. '모델 실험대' 및 '공유 모델' 임포트 ---
from shared.config import get_settings, Settings
from shared.models import RouteRequest, RouteResponse

# --- 3. FastAPI 앱 초기화 ---
app = FastAPI()

# --- 4. 프롬프트 템플릿 ---
# (Colab에서 최종 성공한 템플릿)
LOGICAL_ROUTING_PROMPT_TEMPLATE = """
너는 사용자의 질문을 분석하여 'rag-service'와 'search-agent-service' 중 하나로 라우팅하는 AI 에이전트다.

[라우팅 규칙]
1. (A) 'search-agent-service': 도서관의 실시간 소장 정보, 대출 가능 여부, 특정 도서의 위치 등 '실시간' 정보나 '도서관 자체' 정보가 필요할 때.
2. (B) 'rag-service': "AI가 고용에 미치는 영향"처럼 학술적인 주제, 논문, 자료 요약 등 '지식' 자체가 필요할 때.

[출력 포맷]
- 반드시 아래의 JSON 형식을 따라야 한다.
- 다른 말은 절대 덧붙이지 마라.

{{
  "destination": "rag-service",
  "reason": "왜 그렇게 라우팅했는지에 대한 20자 내외의 짧은 이유",
  "keywords": ["질문에서 추출한 핵심 키워드 리스트 (3~5개)"]
}}

[사용자 질문]
{user_query}
"""

# --- 5. '모델 실험대'를 통해 OpenAI 클라이언트 주입 ---
# get_settings()를 통해 .env의 API 키로 OpenAI 클라이언트를 생성합니다.
# (참고: config.py에 OpenAI 클라이언트 생성 로직이 이미 있다고 가정)
# (만약 없다면, settings.OPENAI_API_KEY를 사용해 여기서 client를 생성)

# settings = get_settings()
# client = OpenAI(api_key=settings.OPENAI_API_KEY)
# -> 이 방식보다 'Depends'를 사용하는 것이 FastAPI에서 권장됩니다.

def get_openai_client(settings: Settings = Depends(get_settings)) -> OpenAI:
    # 이 함수는 설정에서 API 키를 가져와 클라이언트를 생성합니다.
    # (이 로직은 config.py로 옮겨도 좋습니다)
    return OpenAI(api_key=settings.OPENAI_API_KEY)


# --- 6. 핵심 로직 함수화 (Colab 테스트 완료) ---
def get_routing_decision(query: str, client: OpenAI) -> Dict:
    """
    Colab에서 테스트 완료된 라우팅 결정 함수.
    이젠 client를 파라미터로 받습니다.
    """
    prompt_message = LOGICAL_ROUTING_PROMPT_TEMPLATE.format(user_query=query)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # 이 부분도 나중엔 settings에서 관리 가능
            messages=[{"role": "system", "content": prompt_message}],
            response_format={"type": "json_object"}
        )
        
        result_json = response.choices[0].message.content
        decision_data = json.loads(result_json)
        
        # Pydantic 모델로 유효성 검사 (필수!)
        validated_response = RouteResponse(**decision_data)
        return validated_response.model_dump() # dict로 반환

    except Exception as e:
        print(f"라우팅 결정 오류: {e}")
        # 오류 발생 시에도 Pydantic 모델 형식으로 반환
        return RouteResponse(
            destination="rag-service", # 기본값
            reason=f"라우팅 결정 중 오류 발생: {e}",
            keywords=[]
        ).model_dump()


# --- 7. FastAPI 엔드포인트 생성 ---
@app.post("/api/strategy/route", response_model=RouteResponse)
async def handle_routing(
    request: RouteRequest, 
    client: OpenAI = Depends(get_openai_client) # '모델 실험대' 연동!
):
    """
    사용자의 질문을 분석하여 적절한 마이크로서비스로 라우팅합니다.
    (rag-service 또는 search-agent-service)
    """
    try:
        decision_dict = get_routing_decision(request.user_query, client)
        # Pydantic 모델로 반환 (FastAPI가 자동으로 JSON 직렬화)
        return RouteResponse(**decision_dict)
    
    except Exception as e:
        # Pydantic 모델을 사용한 구조화된 오류 응답
        error_response = RouteResponse(
            destination="rag-service",
            reason=f"API 처리 중 심각한 오류: {e}",
            keywords=[]
        ).model_dump()
        raise HTTPException(
            status_code=500,
            detail=error_response
        )

# (기타 /api/strategy/generate 등 다른 엔드포인트들...)