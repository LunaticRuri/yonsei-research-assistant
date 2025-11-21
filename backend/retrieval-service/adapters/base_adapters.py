from abc import ABC, abstractmethod
from typing import List, Dict, Any
from shared.models import Document, SearchRequest

class BaseRetriever(ABC):
    """모든 검색 어댑터가 구현해야 하는 인터페이스"""
    
    @abstractmethod
    async def request_to_search_params(self, request: SearchRequest) -> Any:
        """
        LLM 기반으로 SearchRequest를 어댑터별 검색 파라미터 객체로 변환
        
        Args:
            request (SearchRequest): 통합 검색 요청 객체
        Returns:
            Any: 어댑터별로 정의된 검색 파라미터 객체
        """
        pass

    @abstractmethod
    async def search(self, search_params) -> List[Document]:
        """
        통일된 검색 메서드
        
        Args:
            search_params : 각 어댑터별로 변환된 검색 파라미터 객체
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