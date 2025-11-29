import os
import time
import torch
from openai import OpenAI
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from peft import PeftModel

class QueryTranslationService:
    def __init__(self, adapter_path: str = None):
        print("⚙️ [Init] QueryTranslationService 초기화 중...")
        
        # 1. API 클라이언트
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
            print("✅ OpenAI Client 연결 성공")
        else:
            self.client = None
            print("⚠️ OpenAI API Key가 없습니다. API 모드는 작동하지 않습니다.")

        # 2. LoRA 모델 (Mocking 지원)
        self.lora_model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if adapter_path and os.path.exists(adapter_path):
            try:
                base_model_id = "paust/pko-chat-t5-large"
                print(f"🔄 LoRA 모델 로드 시도: {adapter_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(base_model_id)
                base_model = AutoModelForSeq2SeqLM.from_pretrained(
                    base_model_id, 
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map=self.device
                )
                self.lora_model = PeftModel.from_pretrained(base_model, adapter_path)
                self.lora_model.eval()
                print("✅ LoRA 모델 로드 완료!")
            except Exception as e:
                print(f"❌ LoRA 로드 실패: {e}")
        else:
            print(f"⚠️ 모델 경로 없음({adapter_path}). LoRA는 [Mock] 모드로 동작합니다.")

    def _generate_by_api(self, query):
        if not self.client: return "[Error] API Key Missing"
        prompt = f"질문: {query}\n검색 키워드를 쉼표로 구분해 추출해줘." 
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[Error] API Call Failed: {str(e)}"

    def _generate_by_lora(self, query):
        # [Mocking Logic]
        if self.lora_model is None:
            time.sleep(0.5) 
            return f"[Mock] '{query}'에 대한 로컬 키워드 (모델 미연결)"
            
        input_text = f"### 질문:\n{query}\n### 핵심 검색어 목록:"
        inputs = self.tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True).to(self.device)
        with torch.no_grad():
            outputs = self.lora_model.generate(**inputs, max_new_tokens=128)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def generate_keywords(self, query, mode="api"):
        start_time = time.time()
        if mode == "api": result = self._generate_by_api(query)
        elif mode == "lora": result = self._generate_by_lora(query)
        else: result = "Invalid Mode"
        
        return {
            "query": query, "mode": mode, "keywords": result,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
