#**********************************************
# DEPRICIATED!
#**********************************************
from openai import OpenAI
import json
import sys
import os

# shared 모듈 경로 설정
from shared.models import RoutingDecision

# [수정된 프롬프트] 키워드 필드명을 명확하게 강제합니다.
LOGICAL_ROUTING_PROMPT = """
당신은 사용자의 질문을 분석하여 검색 전략을 수립하는 'Strategy Agent'입니다.

[지시사항]
1. 질문의 의도를 파악하여 적절한 검색 서비스(route)를 선택하세요.
2. 질문을 검색 엔진에 입력하기 좋은 **3~5개의 명사형 키워드**로 변환하세요.
3. **반드시 아래 JSON 형식을 엄격하게 지키세요.** (키 이름 중요!)

[라우팅 규칙]
- 'rag_service': 학술, 논문, 연구, 전문 지식, 깊이 있는 설명
- 'search_agent_service': 날씨, 위치, 단순 사실, 실시간 정보, 도서관 안내

[출력 포맷 JSON 예시]
{{
    "route": "rag_service",
    "reason": "사용자가 학술적인 연구 결과를 요청했기 때문입니다.",
    "search_queries": ["굴패각", "소성 가공", "액상소석회", "화학적 특성"]
}}

[주의사항]
- 'search_queries'라는 키 이름을 정확히 사용하세요. ('keywords' 금지)
- 불필요한 서술 없이 JSON만 출력하세요.

[사용자 질문]
{user_query}
"""

async def get_routing_decision(user_query: str, client: OpenAI) -> RoutingDecision:
    prompt = LOGICAL_ROUTING_PROMPT.format(user_query=user_query)

    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {"role": "system", "content": "You are a helpful research assistant. Output must be valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}, 
            temperature=0.0 
        )

        content = response.choices[0].message.content
        
        # [디버깅] LLM이 실제로 뱉은 원본 텍스트 확인 (여기서 원인을 알 수 있음!)
        print(f"🔍 [LLM Raw Output]: {content}")

        result_json = json.loads(content)

        # [안전장치] LLM이 'keywords'나 'queries'로 잘못 줬을 경우를 대비해 데이터를 보정합니다.
        if "search_queries" not in result_json:
            print("⚠️ 'search_queries' 키가 없어서 대체 키를 찾습니다...")
            if "keywords" in result_json:
                result_json["search_queries"] = result_json["keywords"]
            elif "queries" in result_json:
                 result_json["search_queries"] = result_json["queries"]
            elif "extracted_keywords" in result_json:
                result_json["search_queries"] = result_json["extracted_keywords"]
            else:
                # 정말 아무것도 없으면 원본 질문이라도 넣음
                result_json["search_queries"] = [user_query]

        # Pydantic 모델 변환
        return RoutingDecision(**result_json)

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return RoutingDecision(
            route="rag_service", 
            reason=f"Error: {str(e)}", 
            search_queries=[user_query] 
        )
