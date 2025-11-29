
import httpx
import os
from shared.models import RetrievalRequest

# 환경변수에서 URL 가져오기 (없으면 로컬 기본값)
RETRIEVAL_URL = os.getenv("RETRIEVAL_SERVICE_URL", "http://localhost:8003/api/v1/search")

class RetrievalClient:
    async def request_search(self, query: str, keywords: list):
        payload = RetrievalRequest(
            query=query,
            keywords=keywords,
            top_k=3
        ).model_dump()
        
        print(f"📡 [Retrieval Client] 검색 요청 전송: {RETRIEVAL_URL}")
        print(f"   ㄴ Payload: {payload}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(RETRIEVAL_URL, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            # [Mocking] 실제 서비스가 없어도 죽지 않게 가짜 데이터 반환
            print(f"⚠️ [Mock] 검색 서비스 연결 실패 (테스트 환경): {e}")
            return {
                "status": "mock_success",
                "documents": [
                    {"title": "가짜 논문 1", "content": "검색 서비스가 아직 연결되지 않았습니다."},
                    {"title": "가짜 논문 2", "content": "이것은 테스트용 더미 데이터입니다."}
                ]
            }
