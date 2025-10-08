import os
import json
import logging
from typing import List
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate_synonyms(self, keyword: str, research_topic: str) -> List[str]:
        """LLM을 사용하여 키워드에 대한 학술적 동의어를 생성합니다."""
        prompt = f"""
        당신은 한국어 학술 연구 전문가입니다.
        연구 주제: "{research_topic}"
        핵심 키워드: "{keyword}"
        위 연구 주제의 맥락에서 "{keyword}"의 학술적 동의어 또는 매우 유사한 의미의 유의어를 3개만 제시해주세요.
        결과는 반드시 'synonyms'라는 키를 가진 JSON 객체 형식(예: {{"synonyms": ["유의어1", "유의어2"]}})으로만 응답해야 합니다.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            content = json.loads(response.choices[0].message.content)
            return content.get("synonyms", [])
        except Exception as e:
            logger.error(f"LLM API(동의어) 호출 중 오류 발생: keyword={keyword}", exc_info=True)
            raise e

    async def generate_related_terms(self, keywords: List[str], research_topic: str) -> List[str]:
        """LLM을 사용하여 키워드와 관련된 용어들을 생성합니다."""
        prompt = f"""
        당신은 특정 연구 주제에 대한 검색 전략을 수립하는 연구 지원 전문가입니다.
        연구 주제: "{research_topic}"
        핵심 키워드: {keywords}
        위 연구 주제 및 핵심 키워드와 맥락적으로 관련된 용어들을 5개 제안해주세요. 예를 들어, 상위 개념어, 하위 개념어, 연구 방법론, 관련 현상 등을 포함할 수 있습니다.
        결과는 반드시 'related_terms'라는 키를 가진 JSON 객체 형식(예: {{"related_terms": ["관련어1", "관련어2"]}})으로만 응답해야 합니다.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            content = json.loads(response.choices[0].message.content)
            return content.get("related_terms", [])
        except Exception as e:
            logger.error(f"LLM API(관련어) 호출 중 오류 발생: keywords={keywords}", exc_info=True)
            raise e

    async def identify_academic_fields(self, keywords: List[str], research_topic: str) -> List[str]:
        """LLM을 사용하여 연구 주제와 관련된 학문 분야를 식별합니다."""
        prompt = f"""
        당신은 학술 데이터베이스의 주제 분류 전문가입니다.
        연구 주제: "{research_topic}"
        핵심 키워드: {keywords}
        위 연구 주제를 가장 잘 다루는 학문 분야를 3개 식별해주세요. 예를 들어, "심리학", "사회학", "컴퓨터 과학", "의학", "경제학", "교육학" 등이 있습니다.
        결과는 반드시 'academic_fields'라는 키를 가진 JSON 객체 형식(예: {{"academic_fields": ["분야1", "분야2"]}})으로만 응답해야 합니다.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            content = json.loads(response.choices[0].message.content)
            return content.get("academic_fields", [])
        except Exception as e:
            logger.error(f"LLM API(학문분야) 호출 중 오류 발생: keywords={keywords}", exc_info=True)
            raise eco