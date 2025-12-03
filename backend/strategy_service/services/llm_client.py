#**********************************************
# DEPRICIATED!
#**********************************************
# backend/strategy-service/services/llm_client.py (최종 수정본)

# [삭제] import os
# [삭제] from dotenv import load_dotenv
import json
import logging
from typing import List
from openai import AsyncOpenAI

# [삭제] load_dotenv() - 이젠 config.py가 이 역할을 합니다.

# [추가] config.py에서 settings와 프롬프트 변수들을 임포트합니다.
#       (services/ 폴더 안에 있으니 ..config 로 상위 폴더 접근)
from ..config import settings, PROMPT_GEN_SYNONYMS, PROMPT_GEN_RELATED, PROMPT_ID_ACADEMIC

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # [삭제] self.api_key = os.getenv("OPENAI_API_KEY")
        # [삭제] if not self.api_key: ...
        
        # [변경] settings 객체를 사용하여 API 키 설정
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_synonyms(self, keyword: str, research_topic: str) -> List[str]:
        """LLM을 사용하여 키워드에 대한 학술적 동의어를 생성합니다."""
        
        # [변경] 하드코딩된 프롬프트 대신, config에서 불러온 템플릿 사용
        #       .format()을 사용해 변수들을 채워줍니다.
        prompt_content = PROMPT_GEN_SYNONYMS.format(
            research_topic=research_topic,
            keyword=keyword
        )
        
        try:
            response = await self.client.chat.completions.create(
                # [변경] config에서 모델 이름 가져오기
                model=settings.STRATEGY_LLM_MODEL, 
                messages=[{"role": "user", "content": prompt_content}],
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
        
        # [변경] 하드코딩된 프롬프트 대신, config에서 불러온 템플릿 사용
        prompt_content = PROMPT_GEN_RELATED.format(
            research_topic=research_topic,
            keywords=keywords
        )
        
        try:
            response = await self.client.chat.completions.create(
                # [변경] config에서 모델 이름 가져오기
                model=settings.STRATEGY_LLM_MODEL,
                messages=[{"role": "user", "content": prompt_content}],
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
        
        # [변경] 하드코딩된 프롬프트 대신, config에서 불러온 템플릿 사용
        prompt_content = PROMPT_ID_ACADEMIC.format(
            research_topic=research_topic,
            keywords=keywords
        )
        
        try:
            response = await self.client.chat.completions.create(
                # [변경] config에서 모델 이름 가져오기
                model=settings.STRATEGY_LLM_MODEL,
                messages=[{"role": "user", "content": prompt_content}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            content = json.loads(response.choices[0].message.content)
            return content.get("academic_fields", [])
        except Exception as e:
            logger.error(f"LLM API(학문분야) 호출 중 오류 발생: keywords={keywords}", exc_info=True)
            raise e