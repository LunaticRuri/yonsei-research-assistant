import os
import time
import torch
import asyncio
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel
from langchain_core.prompts import ChatPromptTemplate
import re

# 부품들 가져오기
from strategy_service.core.providers.openai_handler import OpenAIHandler
from strategy_service.core.providers.gemini_handler import GeminiHandler

# NOTE: 아래 두 핸들러는 현재 주석 처리 상태
# from strategy_service.core.providers.cohere_handler import CohereHandler
# from strategy_service.core.providers.upstage_handler import UpstageHandler

from shared.models import StrategyServiceMode
from shared.config import settings

import logging


class QueryTranslationService:
    def __init__(self, adapter_path: str = None):
        print("[Init] QueryTranslationService (Factory Mode) 초기화...")
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(settings.console_handler)
        self.logger.addHandler(settings.file_handler)

        # 1. API 핸들러 등록 (확장성 포인트!)
        self.api_providers = {
            "openai": OpenAIHandler(settings.OPENAI_API_KEY),
            "gemini": GeminiHandler(settings.GEMINI_API_KEY)
        }
        
        """
        원래 코드:
        # 1. API 핸들러 등록 (확장성 포인트!)
        self.api_providers = {
            "openai": OpenAIHandler(os.getenv("OPENAI_API_KEY")),
            "gemini": GeminiHandler(os.getenv("GEMINI_API_KEY")), 
            "upstage": UpstageHandler(os.getenv("UPSTAGE_API_KEY")),
            "cohere": CohereHandler(os.getenv("COHERE_API_KEY"))
        }
        """

        # 2. LoRA 모델 로드 (기존 로직 유지)
        self.lora_model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if adapter_path and os.path.exists(adapter_path):
            try:
                base_model_id = "paust/pko-flan-t5-large"
                self.logger.info(f"🔄 LoRA 모델 로드 시도: {adapter_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(base_model_id)
                base_model = AutoModelForSeq2SeqLM.from_pretrained(
                    base_model_id, 
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map=self.device
                )
                self.lora_model = PeftModel.from_pretrained(base_model, adapter_path)
                self.lora_model.eval()
                self.logger.info("✅ LoRA 모델 로드 완료!")
            except Exception as e:
                self.logger.error(f"❌ LoRA 로드 실패: {e}")
        else:
            self.logger.warning(f"⚠️ 모델 경로 없음({adapter_path}). LoRA는 [Mock] 모드로 동작합니다.")

    async def _generate_by_lora(self, query):
        
        if self.lora_model is None:
            await asyncio.sleep(0.5) 
            return f"[Mock] '{query}'에 대한 로컬 키워드 (모델 미연결)"

        def text_cleaning(text):
            if not isinstance(text, str):
                return ""

            text = text.replace('\n', ' ')
            text = re.sub(r'[^가-힣a-zA-Z0-9 :,]', ',', text)
            if ":" in text:
                first, rest = text.split(":", 1)
                rest = rest.replace(":", ",")
                text = first + ":" + rest

            no_words=['혹은', '및',' 등', '또는', '에 대한', '에 대해', '에 관한', '에 관해', '관련']
            for word in no_words:
                text = text.replace(word, ',')
            
            text = re.sub(r'\s*,+\s*', ',', text)
            text = re.sub(r'(?<![가-힣A-Za-z0-9]),|,(?![가-힣A-Za-z0-9])', '', text)
            text = text.strip()

            return text
        
        def run_inference():
            input_text = ChatPromptTemplate.from_messages(
                [
                    ("system", "지금부터 당신은 대학 학술 정보원의 사서입니다. 당신은 정보 이용자가 원하는 자료를 가장 효과적으로 검색할 수 있도록 도와야 합니다."),
                    ("human", """### 질문: {question}\n            저의 '질문'을 해결하기 위해 제가 검색 엔진에 입력할 '핵심 검색어(Keywords)'들을 쉼표(,)로 구분하여 추출해 주세요. 문장이 아닌 명사형 단어 목록으로만 답변해 주세요. 금지어: '특징', '관련', '선행' ,'연구', '논문', '문헌'""")
                    ]
            )
            input_text = input_text.format_messages(question=query)
            input_text = "\n".join([m.content for m in input_text])
            inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True).to(self.device)
            with torch.no_grad():
                outputs = self.lora_model.generate(**inputs, 
                                                   max_new_tokens=128, 
                                                   num_beams=3,
                                                   repetition_penalty=1.2, 
                                                   no_repeat_ngram_size=2,
                                                   early_stopping=True
                                                   )
                
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        decode = await asyncio.to_thread(run_inference)
        
        self.logger.debug(f"LoRA 생성 결과 (전처리 전): {decode}")

        processed_output = text_cleaning(decode)

        self.logger.debug(f"LoRA 생성 결과 (전처리 후): {processed_output}")
        return processed_output

    async def generate_keywords(self, query, mode: StrategyServiceMode):
        start_time = time.time()
        result = ""
        try:
            # 1. LoRA 모드
            if mode == "lora":
                result = await self._generate_by_lora(query)
            
            # 2. API 모드 (동적 선택)
            elif mode in self.api_providers:
                handler = self.api_providers[mode]
                result = await handler.generate_keywords(query)
            
            # 3. 지원하지 않는 모드
            else:
                self.logger.error(f"지원하지 않는 모드: {mode} -> 기본값 반환")
                raise ValueError("Unsupported mode")
            
            return {
                "query": query, 
                "mode": mode, 
                "keywords": result,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            self.logger.error(f"키워드 생성 실패: {e}, 모드: {mode} -> 기본값 반환")
            return {
                "query": query, 
                "mode": mode, 
                "keywords": query,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
