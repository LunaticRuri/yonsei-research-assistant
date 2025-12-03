import logging
import time

from shared.models import SearchRequest, RetrievalResult, GenerationRequest
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
        self.logger.info(f"Starting retrieval for queries")
        raw_documents = await self.retriever.retrieve_all(request)
        
        if not raw_documents:
            self.logger.warning("No documents retrieved")
            return RetrievalResult(
                documents=[],
                metadata={'error': 'No documents found'},
                needs_requestioning=True
            )
        
        # Step 2: Rerank + Fusion
        self.logger.info(f"Reranking {len(raw_documents)} documents")
        ranked_documents = await self.ranker.rerank_and_fuse(
            documents=raw_documents,
            user_query=request.user_query
        )
        
        # Step 3: Modified-CRAG 평가
        # 일반적인 CRAG(Corrective RAG)의 Knowledge Refinement 단계, 특히 decompose는 사실 관계를 검증하는 QA 시스템에 최적화되어 있다.
        # 현 시스템은 자료 추천 및 소개 성격이 강하므로, 메타 데이터(초록, 소개)가 사용자의 연구 의도나 관심사와 얼마나 '의미적으로 부합하는지'를 판단하는 것이 중요하다.
        # user_query를 '주제', '의도', '제약' 관점으로 분해하고 각 문서가 이러한 요소들과 얼마나 잘 맞는지를 평가하는 방식으로 CRAG를 수정하였다.
        # [ ]: 제대로 작동하는지 테스트 필요!
        self.logger.info("Evaluating document quality with Modified-CRAG")
        
        self.logger.info("  - Analyzing user query for decomposition")
        analyzed_query = await self.refiner.analyze_user_query(
            user_query=request.user_query
        )
        
        crag_results = await self.refiner.evaluate_relevance(
            documents=ranked_documents,
            analyzed_user_query=analyzed_query
        )
        
        # Step 4: 품질 필터링
        filtered_documents = self.refiner.filter_by_quality(crag_results)
        
        # Step 5: 질문 또는 검색 전략 재검토 필요 여부 판단
        needs_requestioning = self.refiner.needs_requestioning(crag_results)
        
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
        retrieval_result = RetrievalResult(
            documents=filtered_documents,
            metadata=metadata,
            needs_requestioning=needs_requestioning
        )

        return GenerationRequest(
            query=request.user_query,
            retrieval_result=retrieval_result
        )