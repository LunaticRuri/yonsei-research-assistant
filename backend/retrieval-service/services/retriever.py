from typing import List, Dict
from adapters import BaseRetriever, LibraryAdapter, VectorDBAdapter
from shared.models import Document, SearchRequest
from config import settings
import asyncio
import logging

class RetrieverService:
    """Strategy Service의 라우팅 결정을 실행"""
    
    def __init__(self):
        # 사용 가능한 어댑터 등록
        self.adapters: Dict[str, BaseRetriever] = {
            'yonsei_library': LibraryAdapter(),
            'vector_db': VectorDBAdapter(
                index_path=settings.FAISS_INDEX_PATH,
                embedding_model=settings.VECTOR_EMBEDDING_MODEL
            )
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
            
            # Multi-query 각각 실행
            for query in request.queries:
                tasks.append(
                    self._search_with_metadata(
                        adapter=adapter,
                        query=query,
                        filters=request.filters,
                        top_k=request.top_k,
                        route=route
                    )
                )
        
        # 병렬 실행
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
    
    async def _search_with_metadata(
        self,
        adapter: BaseRetriever,
        query: str,
        filters: Dict,
        top_k: int,
        route: str
    ) -> List[Document]:
        """단일 검색 + 메타데이터 보강"""
        try:
            docs = await adapter.search(query, filters, top_k)
            
            # 소스 정보 추가 (나중에 Fusion에서 사용)
            for doc in docs:
                doc.metadata['search_query'] = query
                doc.metadata['data_source'] = route
            
            return docs
            
        except Exception as e:
            self.logger.error(
                f"Search failed [adapter={route}, query={query}]: {e}"
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