from typing import List, Dict
import asyncio
import logging

from retrieval_service.adapters.base_adapters import BaseRetriever
from retrieval_service.adapters.library_holdings_adapter import LibraryHoldingsAdapter
from retrieval_service.adapters.electronic_resources_adapter import ElectronicResourcesAdapter
from retrieval_service.adapters.vectordb_adapter import VectorDBAdapter

from shared.models import Document, SearchRequest, RetrievalRoute
from shared.config import settings



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
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(settings.console_handler)
        self.logger.addHandler(settings.file_handler)
    
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
            if route is RetrievalRoute.VECTOR_DB:
                # Vector DB는 별도 처리
                continue
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
        
        # deadlock 방지를 위해 Vector DB 검색은 별도 처리
        if RetrievalRoute.VECTOR_DB in request.routes:
            vector_adapter = self.adapters.get(RetrievalRoute.VECTOR_DB)
            if vector_adapter:
                try:
                    vector_search_params = await vector_adapter.request_to_search_params(request)
                    vector_docs = await vector_adapter.search(vector_search_params, request.top_k)
                    results.append(vector_docs)
                except Exception as e:
                    self.logger.error(f"Vector DB search failed: {e}")

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