from google import genai
from shared.models import SelfRAGPromptType, SelfRAGPromptResult
from shared.config import settings
from generation_service.prompts import (
    SELF_RAG_RELEVANCE_PROMPT_TEMPLATE,
    SELF_RAG_HALLUCINATION_PROMPT_TEMPLATE,
    SELF_RAG_HELPFULNESS_PROMPT_TEMPLATE,
    FINAL_GENERATION_PROMPT_TEMPLATE
)

import logging



class LLMClient:
    """Gemini Client for Generation Service"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.flash_model_name = settings.GEMINI_FLASH_MODEL # self-rag에 사용
        self.pro_model_name = settings.GEMINI_PRO_MODEL # 최종 답변 생성에 사용 (응답 속도가 느려서 일단 제외)

        # NOTE: Self-RAG 평가 기준 점수 조절 가능
        self.pass_threshold = 3  # Self-RAG 평가 통과 기준 점수

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(settings.console_handler)
        self.logger.addHandler(settings.file_handler)
        
    async def generate_self_rag_response(
        self,
        prompt_type: SelfRAGPromptType,
        query_text: str = None,
        documents_text: str = None,
        answer_text: str = None,
    ) -> bool:
        """Generate Self-RAG response from Gemini"""
        try:
            formatted_prompt = ""
            if prompt_type == SelfRAGPromptType.RELEVANCE_CHECK:
                if not query_text or not documents_text:
                    raise ValueError("original_query and documents_text are required for RELEVANCE_CHECK")
                formatted_prompt = SELF_RAG_RELEVANCE_PROMPT_TEMPLATE.format(
                    query_text=query_text,
                    documents_text=documents_text
                )
            elif prompt_type == SelfRAGPromptType.HALLUCINATION_CHECK:
                if not answer_text or not documents_text:
                    raise ValueError("answer_text and documents_text are required for HALLUCINATION_CHECK")
                formatted_prompt = SELF_RAG_HALLUCINATION_PROMPT_TEMPLATE.format(
                    answer_text=answer_text,
                    documents_text=documents_text
                )
            elif prompt_type == SelfRAGPromptType.HELPFULNESS_CHECK:
                if not query_text or not answer_text:
                    raise ValueError("original_query and answer_text are required for HELPFULNESS_CHECK")
                formatted_prompt = SELF_RAG_HELPFULNESS_PROMPT_TEMPLATE.format(
                    query_text=query_text,
                    answer_text=answer_text
                )
            else:
                raise ValueError(f"Unsupported prompt type: {prompt_type}")
            
            response = await self.client.aio.models.generate_content(
                model=self.flash_model_name,
                contents=formatted_prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': SelfRAGPromptResult
                }
            )
            result: SelfRAGPromptResult = response.parsed
            
            if not result:
                raise ValueError("Failed to parse Self-RAG response")
            
            if result.evaluation >= self.pass_threshold:
                self.logger.info(f"Self-RAG {prompt_type.value} check passed with score {result.evaluation}")
                return True
            else:
                self.logger.info(f"Self-RAG {prompt_type.value} check failed with score {result.evaluation}")
                self.logger.info(f"Reason: {result.reason}")
                return False
            
        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise
    
    async def generate_final_response(
        self,
        query_text: str,
        documents_text: str
    ) -> str:
        """Generate final response from Gemini Pro model"""
        try:
            response = await self.client.aio.models.generate_content(
                model=self.flash_model_name,
                contents=FINAL_GENERATION_PROMPT_TEMPLATE.format(
                    query_text=query_text,
                    documents_text=documents_text
                )
            )
            return response.text
            
        except Exception as e:
            self.logger.error(f"Gemini Pro API call failed: {e}")
            raise
