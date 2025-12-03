from google import genai
from strategy_service.core.providers.base import BaseAPIHandler

class GeminiHandler(BaseAPIHandler):
    def __init__(self, api_key: str):
        # 모델명은 최신 버전인 'gemini-2.0-flash'로 유지합니다.
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=api_key,
            temperature=0
        )

    async def generate_keywords(self, query: str) -> str:
        # 동기(Sync) 방식으로 invoke 사용 (async await 문제 방지)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "지금부터 당신은 대학 학술 정보원의 사서입니다. 당신은 정보 이용자가 원하는 자료를 가장 효과적으로 검색할 수 있도록 도와야 합니다."),
                ("human", """### 질문: {query}
                저의 '질문'을 해결하기 위해 제가 검색 엔진에 입력할 '핵심 검색어(Keywords)'들을 쉼표(,)로 구분하여 추출해 주세요. 문장이 아닌 명사형 단어 목록으로만 답변해 주세요. 금지어: '특징', '연구', '논문'""")
            ]
        )
        
        chain = prompt | self.model
        try:
            # invoke 사용
            response = chain.invoke({"query": query})
            return str(response.content)
        except Exception as e:
            return f"[Error] Gemini Call Failed: {e}"
