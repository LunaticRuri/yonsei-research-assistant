import json
from openai import OpenAI 
from shared.models import RoutingDecision 

# 1. 프롬프트 (동일)
LOGICAL_ROUTING_PROMPT_TEMPLATE = """
당신은 연세대학교 학술 정보를 위한 '중앙 라우터'입니다.
사용자의 질문을 분석하여 어떤 서비스로 보내야 할지 결정해야 합니다.

선택 가능한 경로는 2가지입니다:
[1] rag_service: 연세대학교 도서관의 '책', '교재', '학술 논문' 등 **'학내 자료'** 검색
[2] search_agent_service: '소비자법이란?', '오늘 날씨' 등 **'일반 웹 검색'**

사용자의 질문: "{user_query}"

JSON 형식으로 "route"와 "reason"을 분리해서 출력하세요.
"route" 값은 반드시 "[1] rag_service" 또는 "[2] search_agent_service" 중 하나여야 합니다.
"reason" 값은 왜 그렇게 판단했는지 간단한 이유를 한국어로 작성하세요.

JSON:
"""

# 2. 라우팅 결정 로직 (수정됨)
# [!] get_routing_decision 함수 자체는 'async def'로 유지합니다. (테스트 스크립트 때문)
async def get_routing_decision(query: str, llm_client: OpenAI) -> RoutingDecision:
    """
    사용자 쿼리를 받아 LLM을 통해 라우팅 경로를 결정합니다.
    """
    try:
        prompt = LOGICAL_ROUTING_PROMPT_TEMPLATE.format(user_query=query)
        
        # [!] 수정: 'await' 키워드를 제거했습니다!
        #     (llm_client.chat.completions.create는 동기 함수이므로)
        response = llm_client.chat.completions.create(
            model="gpt-4o", # 또는 config에서 가져온 모델
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        response_data = json.loads(response.choices[0].message.content)
        
        decision = RoutingDecision(**response_data)
        return decision

    except json.JSONDecodeError as e:
        print(f"[오류] JSON 파싱 실패: {e}")
        return RoutingDecision(route="[1] rag_service", reason="JSON 파싱 오류, 기본 RAG로 라우팅")
    except Exception as e:
        print(f"[오류] API 호출 중 문제 발생: {e}")
        return RoutingDecision(route="[1] rag_service", reason=f"API 오류 ({e}), 기본 RAG로 라우팅")