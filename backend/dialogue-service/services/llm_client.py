import openai
from typing import Optional
from shared.config import settings
import logging

logger = logging.getLogger(__name__)

class LLMClient:
    """OpenAI GPT-4o와의 통신을 담당하는 클라이언트"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )
        self.model = "gpt-4o"
    
    async def generate_response(
        self, 
        prompt: str, 
        max_tokens: Optional[int] = 1000,
        temperature: float = 0.7
    ) -> str:
        """LLM으로부터 응답 생성"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 연세대학교의 학술 연구 보조 AI '수리조교'입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}  # JSON 응답 강제
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise
    
    async def generate_structured_response(
        self, 
        prompt: str, 
        response_schema: dict
    ) -> dict:
        """구조화된 JSON 응답 생성"""
        structured_prompt = f"""
        {prompt}
        
        Please respond in JSON format following this schema:
        {response_schema}
        """
        
        response = await self.generate_response(structured_prompt)
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            # 기본 응답 반환
            return {"error": "Failed to parse response"}
    
    def estimate_tokens(self, text: str) -> int:
        """텍스트의 대략적인 토큰 수 추정"""
        # 대략적인 추정: 1 토큰 ≈ 4 글자 (한국어)
        return len(text) // 3