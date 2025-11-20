from abc import ABC, abstractmethod
from typing import List, Dict, Any
from shared.models import Document

class BaseRetriever(ABC):
    """모든 검색 어댑터가 구현해야 하는 인터페이스"""
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        filters: Dict[str, Any] = None,
        top_k: int = 10
    ) -> List[Document]:
        """
        통일된 검색 메서드
        
        Args:
            query: 검색 쿼리 (자연어 또는 키워드)
            filters: 데이터 소스별 필터 (예: 발행연도, 저자 등)
            top_k: 반환할 최대 문서 수
            
        Returns:
            List[Document]: 표준화된 Document 객체 리스트
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """데이터 소스 연결 상태 확인"""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """데이터 소스 식별자 (예: 'yonsei_library', 'vector_db')"""
        pass