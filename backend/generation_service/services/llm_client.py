import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import Optional, Dict, Any, List
from shared.config import settings
import logging
import json

logger = logging.getLogger(__name__)

class LLMClient:
    """Gemini Client for Generation Service"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL or "gemini-1.5-flash"
        
    def _convert_messages_to_gemini(self, messages: List[Dict[str, str]]) -> tuple[str, List[Dict[str, Any]]]:
        """
        Convert OpenAI style messages to Gemini format.
        Returns (system_instruction, contents)
        """
        system_instruction = None
        contents = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [content]})
                
        return system_instruction, contents

    async def generate_response(
        self, 
        messages: list[dict],
        max_tokens: Optional[int] = 2000,
        temperature: float = 0.7,
        response_format: Optional[dict] = None
    ) -> str:
        """Generate response from Gemini"""
        try:
            system_instruction, contents = self._convert_messages_to_gemini(messages)
            
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
            
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            
            if response_format and response_format.get("type") == "json_object":
                generation_config.response_mime_type = "application/json"

            # Safety settings - block few things for research assistant
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            response = await model.generate_content_async(
                contents,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    async def generate_json(
        self, 
        messages: list[dict],
        max_tokens: Optional[int] = 2000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate JSON response"""
        try:
            content = await self.generate_response(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"JSON generation failed: {e}")
            raise
