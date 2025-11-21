from typing import List
from .base_adapters import BaseRetriever
from config import settings
from scrapers.electronic_resources_scraper import ElectronicResourcesScraper, ElectronicSearchParams
from scrapers.search_params import AdditionalQuery, YearRange
from shared.models import (
    RetrievalRoute,
    Document,
    SearchRequest,
    ElectronicSearchField,
    ElectronicResourceInfo
)
import logging

class ElectronicResourcesAdapter(BaseRetriever):
    """연세대학교 학술정보원 전자자료 어댑터"""
    
    def __init__(self):
        self.scraper = ElectronicResourcesScraper(
            user_id=settings.YONSEI_ID,
            user_pw=settings.YONSEI_PW
        )
        self.logger = logging.getLogger(__name__)
    
    async def request_to_search_params(self, request: SearchRequest) -> ElectronicSearchParams:
        """
        SearchRequest를 ElectronicSearchParams 객체로 변환
        
        Args:
            request (SearchRequest): 통합 검색 요청 객체
        Returns:
            ElectronicSearchParams: 전자자료 어댑터용 검색 파라미터 객체
        """
        queries = request.queries
        filters = request.filters
        
        query = queries.query_1
        search_field = queries.search_field_1 if isinstance(queries.search_field_1, ElectronicSearchField) else ElectronicSearchField.TOTAL
        year_range = None
        academic_journals_only = True
        foreign_language = True

        # 기본 쿼리 설정
        
        additional_queries = []
        if queries.query_2:
            if isinstance(queries.search_field_2, ElectronicSearchField):
                search_field_2 = queries.search_field_2
            else:
                search_field_2 = ElectronicSearchField.TOTAL
            
            additional_queries.append(
                {
                    "search_field": search_field_2,
                    "query": queries.query_2,
                    "operator": queries.operator_1
                }
            )

        if queries.query_3:
            if isinstance(queries.search_field_3, ElectronicSearchField):
                search_field_3 = queries.search_field_3
            else:
                search_field_3 = ElectronicSearchField.TOTAL
            
            additional_queries.append(
                {
                    "search_field": search_field_3,
                    "query": queries.query_3,
                    "operator": queries.operator_2
                }
            )
        
        # 필터 처리
        if filters.get("year_range"):
            from_year, to_year = filters["year_range"]
            year_range = {"from_year": from_year, "to_year": to_year}
        if filters.get("accademic_journals_only"):
            academic_journals_only = filters["academic_journals_only"]
        if filters.get("foreign_language"):
            foreign_language = filters["foreign_language"]
        
        return ElectronicSearchParams(
            query=query,
            search_field=search_field,
            additional_queries=additional_queries,
            year_range=year_range,
            academic_journals_only=academic_journals_only,
            foreign_language=foreign_language
        )

    async def search(self, search_params: ElectronicSearchParams, top_k: int = 10) -> List[Document]:
        """
        학술정보원 전자자원을 검색하고 그 결과를 표준 Document 형식으로 변환
        """
        try:
            
            # 스크래퍼 호출
            async with self.scraper as scraper:
                raw_results = await scraper.execute_electronic_search(
                    params=search_params,
                    max_results=top_k
                )
            
            # 표준 Document 형식으로 변환
            documents = []
            for item in raw_results:
                # item is ElectronicResourceInfo
                doc = Document(
                    content=self._extract_text(item),
                    metadata={
                        'source': RetrievalRoute.ELECTRONIC_RESOURCES.value,
                        'title': item.title,
                        'author': "; ".join(item.author) if item.author else "",
                        'publication_year': item.publication_year,
                        'link_url': item.link_url,
                        'detail_url': item.detail_url,
                        'abstract': item.abstract,
                        'doi': item.doi
                    },
                    score=1.0, # 초기 점수는 1.0으로 설정
                    doc_id=item.access_id
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Electronic resources search failed: {e}")
            return []
    
    def _extract_text(self, item: ElectronicResourceInfo) -> str:
        """스크래핑 결과에서 검색 가능한 텍스트 추출"""
        parts = [
            item.title,
            item.abstract,
            "; ".join(item.keywords) if item.keywords else ""
        ]
        return ' '.join(filter(None, parts))
    
    async def health_check(self) -> bool:
        """학술정보원 접근 가능 여부 확인"""
        try:
            # 간단한 검색 테스트
            await self.search("토끼", top_k=1)
            return True
        except:
            return False
    
    @property
    def source_name(self) -> str:
        return "yonsei_electronics"
