from typing import List, Dict, Any, Optional
from .base_adapter import BaseRetriever
from shared.models import Document
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

class VectorDBAdapter(BaseRetriever):
    """FAISS 기반 Vector DB 어댑터"""
    
    def __init__(self, index_path: str, embedding_model: str = "BAAI/bge-m3"):
        self.index = faiss.read_index(index_path)
        self.encoder = SentenceTransformer(embedding_model)
        self.logger = logging.getLogger(__name__)
        
        # 메타데이터 저장소 (실제로는 별도 DB 권장)
        self.metadata_store: Dict[int, Dict] = {}
    
    async def search(
        self, 
        query: str, 
        filters: Dict[str, Any] = None,
        top_k: int = 10
    ) -> List[Document]:
        """
        벡터 유사도 검색
        
        filters 예시 (Self-Query 결과):
        {
            'category': 'computer_science',
            'year': {'$gte': 2020},
            'language': 'en'
        }
        """
        try:
            # 1. 쿼리 임베딩
            query_vector = self.encoder.encode([query])[0]
            query_vector = np.array([query_vector], dtype='float32')
            
            # 2. FAISS 검색 (top_k * 2로 오버페칭, 필터링 후 부족할 수 있음)
            distances, indices = self.index.search(query_vector, top_k * 2)
            
            # 3. 메타데이터 필터링
            documents = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS가 결과를 못 찾은 경우
                    continue
                
                metadata = self.metadata_store.get(int(idx), {})
                
                # 필터 적용 (Self-Query 조건 검증)
                if filters and not self._match_filters(metadata, filters):
                    continue
                
                doc = Document(
                    content=metadata.get('text', ''),
                    metadata={
                        'source': 'vector_db',
                        **metadata
                    },
                    score=float(1 / (1 + dist))  # 거리를 유사도로 변환
                )
                documents.append(doc)
                
                if len(documents) >= top_k:
                    break
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    def _match_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Self-Query 필터 조건 검증"""
        for key, condition in filters.items():
            if key not in metadata:
                return False
            
            value = metadata[key]
            
            # 비교 연산자 처리
            if isinstance(condition, dict):
                if '$gte' in condition and value < condition['$gte']:
                    return False
                if '$lte' in condition and value > condition['$lte']:
                    return False
                if '$eq' in condition and value != condition['$eq']:
                    return False
            else:
                if value != condition:
                    return False
        
        return True
    
    async def health_check(self) -> bool:
        """FAISS 인덱스 상태 확인"""
        try:
            return self.index.ntotal > 0
        except:
            return False
    
    @property
    def source_name(self) -> str:
        return "vector_db"