from langchain_core.prompts import ChatPromptTemplate
from langchain_cohere import ChatCohere

from .base import BaseAPIHandler


class CohereHandler(BaseAPIHandler):
    def __init__(self, api_key):
        if api_key:
            self.model = ChatCohere(cohere_api_key=api_key)
        else:
            self.model = None

    def generate_keywords(self, query: str) -> str:
        if not self.model: return "[Error] Cohere API Key Missing"
        # 프롬프트 구성
        prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", "지금부터 당신은 대학 학술 정보원의 사서입니다. 당신은 정보 이용자가 원하는 자료를 가장 효과적으로 검색할 수 있도록 도와야 합니다."),
                    ("human", """### 질문: {query}
                    저의 '질문'을 해결하기 위해 제가 검색 엔진에 입력할 '핵심 검색어(Keywords)'들을 쉼표(,)로 구분하여 추출해 주세요. 문장이 아닌 명사형 단어 목록으로만 답변해 주세요. 금지어: '특징', '연구', '논문'""")
                ]
            )
        chain = prompt | self.model
        try:
            response = chain.invoke({"query": query})
            return str(response.content)
        except Exception as e:
            return f"[Error] Cohere Call Failed: {e}"