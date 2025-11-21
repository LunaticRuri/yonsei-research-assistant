import logging
import time

from shared.models import SearchRequest, RetrievalResult, RankedDocument
from retrieval_service.services.retriever import RetrieverService
from retrieval_service.services.ranker import RankerService
from retrieval_service.services.refiner import RefinerService



class SearchExecutor:
    """전체 검색 파이프라인 조정"""
    
    def __init__(self):
        self.retriever = RetrieverService()
        self.ranker = RankerService()
        self.refiner = RefinerService()
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, request: SearchRequest) -> RetrievalResult:
        """
        전체 Retrieval 파이프라인 실행
        
        흐름:
        1. Retriever: 모든 소스에서 검색
        2. Ranker: Rerank + Fusion
        3. Refiner: CRAG 품질 평가 + 필터링
        """
        start_time = time.time()
        
        # Step 1: 검색
        self.logger.info(f"Starting retrieval for {len(request.queries)} queries")
        raw_documents = await self.retriever.retrieve_all(request)
        
        if not raw_documents:
            self.logger.warning("No documents retrieved")
            return RetrievalResult(
                documents=[],
                crag_analysis=[],
                metadata={'error': 'No documents found'},
                needs_web_search=True
            )
        
        # Step 2: Rerank + Fusion
        # TODO: Rerank 모델 파인 튜닝 후 원래 메소드로 교체
        self.logger.info(f"Reranking {len(raw_documents)} documents")
        # 임시 메소드 사용
        # 원래 메소드는 아래 주석 처리
        # ranked_documents = self.ranker.rerank_and_fuse(
        ranked_documents = self.ranker.tmp_rerank_and_fuse(
            documents=raw_documents,
            user_query=request.user_query
        )
        
        # Step 3: CRAG 평가
        # TODO: Refiner 구현 완료 후 주석 해제
        # [ ]: refiner.py의 CRAG 관련 메소드들 구현 필요
        self.logger.info("Evaluating document quality with CRAG")
        crag_results = await self.refiner.evaluate_relevance(
            documents=ranked_documents,
            user_query=request.user_query
        )
        
        # Step 4: 품질 필터링
        filtered_documents = self.refiner.filter_by_quality(crag_results)
        
        # Step 5: 웹 검색 필요 여부 판단
        # TODO: 이 부분에서 웹 검색보다 키워드 재설정 및 범위 증가 등으로 대응할 수 있음
        needs_web = self.refiner.needs_web_search(crag_results)
        
        # 메타데이터 수집
        elapsed_time = time.time() - start_time
        metadata = {
            'processing_time_seconds': elapsed_time,
            'total_retrieved': len(raw_documents),
            'after_rerank': len(ranked_documents),
            'after_crag': len(filtered_documents),
            'sources_used': list(set(doc.source for doc in ranked_documents))
        }
        
        self.logger.info(
            f"Search completed in {elapsed_time:.2f}s: "
            f"{len(filtered_documents)} final documents"
        )
        
        return RetrievalResult(
            documents=filtered_documents,
            crag_analysis=crag_results,
            metadata=metadata,
            needs_web_search=needs_web
        )