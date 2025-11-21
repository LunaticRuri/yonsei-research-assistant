from typing import List
from .base_adapters import BaseRetriever
from config import settings
from scrapers.library_holdings_scraper import LibraryHoldingsScraper, LibraryHoldingsSearchParams
import os
import sys

# 현재 파일의 위치를 기준으로 프로젝트 루트(yonsei-research-assistant) 경로를 찾아 sys.path에 추가
# 현재위치(search) -> 상위(retrieval-service) -> 상위(backend)
current_dir = os.path.dirname(os.path.abspath(__file__))
service_root = os.path.abspath(os.path.join(current_dir, "../../")) # 2단계 상위로 이동
sys.path.append(service_root)


from scrapers.search_params import AdditionalQuery
from shared.models import (
    Document,
    SearchRequest,
    LibrarySearchField,
    HoldingsMaterialType,
    YearRange,
    LibraryHoldingInfo
)
import logging

class LibraryHoldingsAdapter(BaseRetriever):
    """연세대학교 도서관 소장자료(단행본 등) 어댑터"""
    
    def __init__(self):
        # NOTE: 아마 소장자료 검색은 로그인 쿠키가 없어도 될 듯
        # 혹시 요구되면 아래 줄 주석 해제
        # self.scraper = LibraryHoldingsScraper(user_id=settings.YONSEI_ID, user_pw=settings.YONSEI_PW)
        self.scraper = LibraryHoldingsScraper()
        self.logger = logging.getLogger(__name__)
    
    async def request_to_search_params(self, request: SearchRequest) -> LibraryHoldingsSearchParams:
        """
        LLM 기반으로 SearchRequest를 LibraryHoldingsSearchParams 객체로 변환
        
        Args:
            request (SearchRequest): 통합 검색 요청 객체
        Returns:
            LibraryHoldingsSearchParams: 도서관 소장자료 어댑터용 검색 파라미터 객체
        """
        queries = request.queries
        filters = request.filters
        
        query = queries.query_1
        search_field = queries.search_field_1 if isinstance(queries.search_field_1, LibrarySearchField) else LibrarySearchField.TOTAL
        year_range = None
        material_types = []

        additional_queries = []
        if queries.query_2:
            if isinstance(queries.search_field_2, LibrarySearchField):
                search_field_2 = queries.search_field_2
            else:
                search_field_2 = LibrarySearchField.TOTAL
            
            additional_queries.append(
                AdditionalQuery(
                    search_field= search_field_2,
                    query= queries.query_2,
                    operator= queries.operator_1
                )
            )

        if queries.query_3:
            if isinstance(queries.search_field_3, LibrarySearchField):
                search_field_3 = queries.search_field_3
            else:
                search_field_3 = LibrarySearchField.TOTAL
            
            additional_queries.append(
                AdditionalQuery(
                    search_field= search_field_3,
                    query= queries.query_3,
                    operator= queries.operator_2
                )
            )
        
        # 필터 처리
        if filters.get("year_range"):
            from_year, to_year = filters["year_range"]
            year_range = YearRange(from_year=from_year, to_year=to_year)
        if filters.get("maraterial_types"):
            for t in filters["material_types"]:
                if isinstance(t, HoldingsMaterialType):
                    material_types.append(t)
                else:
                    try:
                        material_types.append(HoldingsMaterialType(t))
                    except ValueError:
                        pass
        
        return LibraryHoldingsSearchParams(
            query=query,
            search_field=search_field,
            additional_queries=additional_queries,
            year_range=year_range,
            material_types=material_types
        )


    async def search(self, search_params: LibraryHoldingsSearchParams, top_k: int = 10) -> List[Document]:
        """
        도서관 소장자료를 검색하고 그 결과를 표준 Document 형식으로 변환
        """
        try:
            # 스크래퍼 호출
            async with self.scraper as scraper:
                raw_results = await scraper.execute_holdings_search(
                    params=search_params,
                    max_results=top_k
                )
            
            # 표준 Document 형식으로 변환
            documents = []
            for item in raw_results:
                # item is LibraryHoldingInfo
                doc = Document(
                    content=self._extract_text(item),
                    metadata={
                        'source': 'yonsei_holdings',
                        'title': item.title,
                        'author': item.author,
                        'publication_info': item.publication_info,
                        'publication_year': item.publication_year,
                        'isbn': item.isbn,
                        'detail_url': item.detail_url,
                        'material_type': item.material_type,
                        'book_description': item.book_description
                    },
                    score=1.0,
                    doc_id=item.access_id
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Library holdings search failed: {e}")
            return []
    
    def _extract_text(self, item: LibraryHoldingInfo) -> str:
        """스크래핑 결과에서 검색 가능한 텍스트 추출"""
        parts = [
            item.title,
            item.author,
            item.book_description
        ]
        return ' '.join(filter(None, parts))
    
    async def health_check(self) -> bool:
        """도서관 접근 가능 여부 확인"""
        try:
            # 간단한 검색 테스트
            await self.search("코끼리", top_k=1)
            return True
        except:
            return False
    
    @property
    def source_name(self) -> str:
        return "yonsei_holdings"
