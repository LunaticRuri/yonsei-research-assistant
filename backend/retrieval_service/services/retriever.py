from typing import List, Dict
from adapters import (
    BaseRetriever, 
    ElectronicResourcesAdapter, 
    LibraryHoldingsAdapter, 
    VectorDBAdapter
)
from shared.models import Document, SearchRequest, RetrievalRoute
from config import settings
import asyncio
import logging

class RetrieverService:
    """Strategy Service의 라우팅 결정을 실행"""
    
    def __init__(self):
        # 사용 가능한 어댑터 등록
        self.adapters: Dict[RetrievalRoute, BaseRetriever] = {
            RetrievalRoute.YONSEI_HOLDINGS: LibraryHoldingsAdapter(),
            RetrievalRoute.YONSEI_ELECTRONICS: ElectronicResourcesAdapter(),
            RetrievalRoute.VECTOR_DB: VectorDBAdapter()
        }
        self.logger = logging.getLogger(__name__)
    
    async def retrieve_all(self, request: SearchRequest) -> List[Document]:
        """
        모든 데이터 소스에서 병렬 검색
        
        Returns:
            중복 제거되지 않은 전체 문서 리스트 (Ranker가 처리)
        """
        all_documents = []
        
        # 각 소스별 검색 태스크 생성
        tasks = []
        for route in request.routes:
            adapter = self.adapters.get(route)
            if not adapter:
                self.logger.warning(f"Unknown route: {route}")
                continue
            
            tasks.append(
                self._retrieve_process(
                    adapter=adapter,
                    request=request,
                    route=route
                )
            )
        
        # 병렬 실행
        # NOTE: 혹시 연세대학교 로그인-로그아웃 겹침 문제로 작동 안되면 직렬로 바꾸기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 수집
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Search task failed: {result}")
                continue
            all_documents.extend(result)
        
        self.logger.info(
            f"Retrieved {len(all_documents)} documents from "
            f"{len(request.routes)} sources"
        )
        
        return all_documents
    
    async def _retrieve_process(
        self,
        adapter: BaseRetriever,
        request: SearchRequest,
        route: RetrievalRoute
    ) -> List[Document]:
        """단일 소스에서 검색 처리"""
        try:
            search_params = await adapter.request_to_search_params(request)
            docs = await adapter.search(search_params, request.top_k)
            
            return docs
            
        except Exception as e:
            self.logger.error(
                f"Search failed [adapter={route}, request={request}]: {e}"
            )
            return []
    
    async def health_check(self) -> Dict[str, bool]:
        """모든 데이터 소스 상태 확인"""
        status = {}
        for name, adapter in self.adapters.items():
            try:
                status[name] = await adapter.health_check()
            except:
                status[name] = False
        return status