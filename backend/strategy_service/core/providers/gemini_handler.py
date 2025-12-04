from google import genai
from strategy_service.core.providers.base import BaseAPIHandler
from pydantic import BaseModel, Field
import logging

from shared.config import settings

KEYWORDS_PROMPT_TEMPLATE = """
당신은 대학 학술정보원의 검색 전문가이다.
주어진 질문(question)에 대해 효과적인 검색어(keywords)를 생성하라.
        
예시
question: "민법상 불법행위 책임(제750조) 성립 요건 중 위법성의 판단 기준을 어떻게 해석해야 하는가?"
keywords: ["불법행위 책임 요건", "위법성 판단 기준"]

주의사항!

1. 검색 키워드는 최소 1개, 그리고 3개 까지 생성 가능. 각 키워드가 서로 중복된 내용을 담으면 안됨.
질문: "천도교의 핵심 교리인 '인내천(人乃天)' 사상이 현대 사회에 어떤 의미를 가지는가?" 인 경우
잘못된 예시:
    키워드: ["천도교 교리", "인내천 사상", "천도교 인내천"]
    -> 키워드가 중복된 내용을 담고 있어서 안됨.
올바른 예시:
    키워드: ["천도교 인내천", "현대 사회"]

2. 키워드는 되도록이면 2개 이하 단어, 검색어가 너무 길거나 복잡하면 안됨.

3. 최대한 명확하고 간단한 키워드로 생성. 질문을 반복하는 키워드보다는 질문을 해결하는 자료(도서, 논문, 학술지)를 찾게 도와주는 키워드가 좋다.

---

question: {}
"""

# Pydantic model for Gemini response
class GeneratedQuestion(BaseModel):
    question: str
    keywords: list[str] = Field(
        default_factory=list,
        description="생성된 검색 키워드 리스트",
        min_items=1,
        max_items=3
    )

class GeminiHandler(BaseAPIHandler):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = settings.GEMINI_FLASH_MODEL
        self.logger = logging.getLogger(__name__)

    async def generate_keywords(self, query: str) -> str:
        formatted_prompt = KEYWORDS_PROMPT_TEMPLATE.format(query)
        
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=formatted_prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': GeneratedQuestion
                }
            )

            parsed_response = response.parsed
            return ', '.join(parsed_response.keywords)

        except Exception as e:
            self.logger.error(f"Gemini API 호출 실패: {e}")
            return ""
