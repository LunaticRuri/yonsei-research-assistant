from google import genai
from shared.config import settings
from shared.models import RoutingRequest, RoutingDecision

import logging

LOGICAL_ROUTING_PROMPT = """
당신은 사용자의 질문과 이에 대한 검색 키워드를 분석하여 검색 경로를 결정하는 전문가이다.

질문의 의도를 파악하여 적절한 검색 경로(routes)를 선택하라.
그러한 경로를 선택한 이유(reason)도 간단히 설명하라.
마땅한 서비스가 없거나 결정하기 어려운 경우, 모든 경로를 선택하라.

선택가능한 경로(다중 선택 가능) (routes)
1. vector_book_db
2. yonsei_holdings
3. yonsei_electronics

[경로 선택 기준]
- 'vector_book_db': 일반적인 지식이나 정보, 전문 분야이지만 기본적인 내용을 담은 도서 검색에 적합
- 'yonsei_holdings': 전문 분야이면서 기본적이거나 중급 수준의 내용을 담은 도서 검색에 적합
- 'yonsei_electronics': 전문 분야 학술 자료 검색에 적합, 일반적인 내용보다는 중급에서 고급 수준의 내용에 적합, 최신 연구나 학술 자료에도 적합

------
사용자 질문: {user_query}
생성된 키워드: {keywords}
"""


class RoutingService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_FLASH_MODEL

        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(settings.console_handler)
        self.logger.addHandler(settings.file_handler)

    async def determine_routing(self, request: RoutingRequest) -> RoutingDecision:

        prompt = LOGICAL_ROUTING_PROMPT.format(
            user_query=request.query,
            keywords=", ".join(request.keywords)
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': RoutingDecision,
                }
            )
        except Exception as e:
            self.logger.error(f"Routing failed: {e}")
            return RoutingDecision(
                routes=["vector_book_db", "yonsei_holdings", "yonsei_electronics"],
                reason="라우팅 결정 실패로 인한 기본값 반환"
            )
        
        return response.parsed