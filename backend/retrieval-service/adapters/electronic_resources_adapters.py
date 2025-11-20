from typing import List, Dict, Any
from base_adapters import BaseRetriever
from config import settings
from scrapers.electronic_resources_scraper import ElectronicResourcesScraper
from shared.models import Document
import logging

class ElectronicResourcesAdapter(BaseRetriever):
    """연세대학교 학술정보원 전자자료 어댑터"""
    
    def __init__(self):
        self.scraper = ElectronicResourcesScraper(
            user_id=settings.YONSEI_ID,
            user_pw=settings.YONSEI_PW
            )
        self.logger = logging.getLogger(__name__)
    
    async def search(
        self, 
        query: str, 
        filters: Dict[str, Any] = None,
        top_k: int = 10
    ) -> List[Document]:
        """
        학술정보원 검색 결과를 표준 Document 형식으로 변환
        
        filters 예시:
        {
            'material_type': 'article',  # 자료유형
            'year_range': (2020, 2024),  # 발행연도
            'language': 'kor'             # 언어
        }
        """
        try:
            # 기존 스크래퍼 호출
            raw_results = await self.scraper.search_books(
                keyword=query,
                limit=top_k
            )
            
            # 표준 Document 형식으로 변환
            documents = []
            for item in raw_results:
                doc = Document(
                    content=self._extract_text(item),
                    metadata={
                        'source': 'yonsei_library',
                        'title': item.get('title', ''),
                        'author': item.get('author', ''),
                        'publisher': item.get('publisher', ''),
                        'year': item.get('year', ''),
                        'isbn': item.get('isbn', ''),
                        'url': item.get('url', ''),
                        'call_number': item.get('call_number', '')
                    },
                    score=1.0  # 초기 점수 (나중에 Ranker가 재계산)
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Library search failed: {e}")
            return []
    
    def _extract_text(self, item: Dict) -> str:
        """스크래핑 결과에서 검색 가능한 텍스트 추출"""
        parts = [
            item.get('title', ''),
            item.get('abstract', ''),
            item.get('keywords', '')
        ]
        return ' '.join(filter(None, parts))
    
    async def health_check(self) -> bool:
        """학술정보원 접근 가능 여부 확인"""
        try:
            # 간단한 검색 테스트
            result = await self.search("test", top_k=1)
            return True
        except:
            return False
    
    @property
    def source_name(self) -> str:
        return "yonsei_library"