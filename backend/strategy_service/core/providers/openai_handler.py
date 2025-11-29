from openai import OpenAI
from .base import BaseAPIHandler

class OpenAIHandler(BaseAPIHandler):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key) if api_key else None

    def generate_keywords(self, query: str) -> str:
        if not self.client:
            return "[Error] OpenAI API Key Missing"

        prompt = f"질문: {query}\n검색 키워드를 쉼표로 구분해 추출해줘."
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[Error] OpenAI Call Failed: {str(e)}"
