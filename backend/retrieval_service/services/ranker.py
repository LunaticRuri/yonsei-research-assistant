from typing import List, Dict
from sentence_transformers import CrossEncoder
import logging
from collections import defaultdict

from retrieval_service.config import settings
from shared.models import Document, RankedDocument

class RankerService:
    """여러 소스의 검색 결과를 융합하고 재순위화"""
    
    def __init__(self):
        # Cross-encoder 모델 로드 (semantic reranking용)
        self.reranker = CrossEncoder(settings.RERANK_MODEL)
        self.logger = logging.getLogger(__name__)
    
    def rerank_and_fuse(
        self,
        documents: List[Document],
        user_query: str,
        method: str = None
    ) -> List[RankedDocument]:
        """
        Rerank + Fusion 파이프라인
        
        Args:
            documents: 여러 소스에서 검색된 원본 문서
            user_query: 사용자 원본 질문 (Cross-encoder 입력)
            method: 'rrf' | 'weighted' | 'cross_encoder'
        
        Returns:
            최종 순위가 매겨진 문서 (top_k개)
        """
        method = method or settings.FUSION_METHOD
        
        # 1. 중복 제거 (동일 content 기준)
        unique_docs = self._deduplicate(documents)
        self.logger.info(f"Deduplicated: {len(documents)} -> {len(unique_docs)}")
        
        # 2. Cross-encoder로 재점수
        reranked = self._cross_encoder_rerank(unique_docs, user_query)
        
        # 3. Fusion 전략 적용
        if method == "rrf":
            final_docs = self._reciprocal_rank_fusion(reranked)
        elif method == "weighted":
            final_docs = self._weighted_fusion(reranked)
        else:  # cross_encoder
            final_docs = reranked
        
        # 4. Top-K 필터링 및 순위 부여
        final_docs = final_docs[:settings.RERANK_TOP_K]
        for rank, doc in enumerate(final_docs, start=1):
            doc.rank = rank
        
        self.logger.info(f"Final ranked documents: {len(final_docs)}")
        return final_docs
    
    def _deduplicate(self, documents: List[Document]) -> List[Document]:
        """Content 기반 중복 제거"""
        seen = set()
        unique = []
        
        for doc in documents:
            # 간단한 해싱 (실제로는 embedding 유사도 비교 권장)
            content_hash = hash(doc.content[:500])
            
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(doc)
        
        return unique
    
    def _cross_encoder_rerank(
        self,
        documents: List[Document],
        query: str
    ) -> List[RankedDocument]:
        """Cross-encoder로 쿼리-문서 관련성 재평가"""
        
        # Batch로 점수 계산
        pairs = [[query, doc.content] for doc in documents]
        scores = self.reranker.predict(pairs)
        
        # RankedDocument로 변환
        ranked = []
        for doc, score in zip(documents, scores):
            ranked_doc = RankedDocument(
                content=doc.content,
                metadata=doc.metadata,
                rerank_score=float(score),
                original_score=doc.score,
                source=doc.metadata.get('data_source', 'unknown'),
                rank=0  # 나중에 설정
            )
            ranked.append(ranked_doc)
        
        # 점수 기준 정렬
        ranked.sort(key=lambda x: x.rerank_score, reverse=True)
        return ranked
    
    def _reciprocal_rank_fusion(
        self,
        documents: List[RankedDocument],
        k: int = 60
    ) -> List[RankedDocument]:
        """
        RRF (Reciprocal Rank Fusion)
        여러 검색 결과의 순위를 조화롭게 융합
        
        RRF_score = Σ 1/(k + rank_i)
        """
        # 소스별로 그룹화
        source_groups = defaultdict(list)
        for doc in documents:
            source_groups[doc.source].append(doc)
        
        # 각 소스 내에서 순위 부여
        rrf_scores = defaultdict(float)
        for source, docs in source_groups.items():
            for rank, doc in enumerate(docs, start=1):
                doc_id = hash(doc.content[:200])  # 임시 ID
                rrf_scores[doc_id] += 1.0 / (k + rank)
        
        # RRF 점수 적용
        for doc in documents:
            doc_id = hash(doc.content[:200])
            doc.rerank_score = rrf_scores[doc_id]
        
        # 재정렬
        documents.sort(key=lambda x: x.rerank_score, reverse=True)
        return documents
    
    def _weighted_fusion(
        self,
        documents: List[RankedDocument],
        weights: Dict[str, float] = None
    ) -> List[RankedDocument]:
        """
        가중치 기반 융합 (소스별 신뢰도 반영)
        """
        weights = weights or {
            'vector_db': 0.6,
            'yonsei_library': 0.4
        }
        
        for doc in documents:
            source = doc.source
            weight = weights.get(source, 0.5)
            
            # 가중 점수 = Cross-encoder * 소스 가중치
            doc.rerank_score = doc.rerank_score * weight
        
        documents.sort(key=lambda x: x.rerank_score, reverse=True)
        return documents