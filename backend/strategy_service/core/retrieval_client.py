
import httpx
import os
from typing import List
from shared.models import (
    SearchRequest, 
    SearchQueries, 
    RetrievalRoute, 
    LibrarySearchField
)

# 환경변수에서 URL 가져오기
RETRIEVAL_URL = os.getenv("RETRIEVAL_SERVICE_URL", "http://localhost:8003/api/v1/search")

class RetrievalClient:
    async def request_search(self, query: str, keywords: List[str]):
        """
        Strategy Service의 결과물(키워드 리스트)을 
        Retrieval Service의 공식 입력 규격(SearchRequest)으로 변환하여 전송합니다.
        """
        
        # 1. 키워드 리스트를 하나의 검색 문자열로 합침 (가장 일반적인 검색 방식)
        combined_query = " ".join(keywords) if keywords else query
        
        # 2. SearchQueries 객체 생성 (회의록 규격 준수)
        # - query_1: 합친 키워드
        # - search_field_1: 전체(TOTAL) 검색
        search_queries = SearchQueries(
            query_1=combined_query,
            search_field_1=LibrarySearchField.TOTAL
        )
        
        # 3. SearchRequest 객체 생성 (최종 봉투)
        # - routes: 벡터DB, 도서관 소장자료 둘 다 검색
        payload = SearchRequest(
            queries=search_queries,
            routes=[RetrievalRoute.VECTOR_DB, RetrievalRoute.YONSEI_HOLDINGS],
            top_k=5,
            user_query=query 
        ).model_dump(mode='json') # JSON 직렬화
        
        print(f"📡 [Retrieval Client] 공식 규격(SearchRequest)으로 검색 요청 전송")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(RETRIEVAL_URL, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"⚠️ [Mock] 검색 서비스 연결 실패 (테스트 환경): {e}")
            return {
                "status": "mock_success",
                "documents": [
                    {"title": "Mock 논문 1", "content": f"'{combined_query}'에 대한 가짜 검색 결과입니다."},
                    {"title": "Mock 논문 2", "content": "Retrieval Service가 연결되면 실제 결과가 나옵니다."}
                ]
            }
