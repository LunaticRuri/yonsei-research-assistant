from typing import List, Dict, Any
from .base_adapters import BaseRetriever
from config import settings
from scrapers.library_holdings_scraper import (
    LibraryHoldingsScraper,
    LibraryHoldingsSearchParams,
    LibrarySearchField,
    HoldingsMaterialType,
    YearRange
)
from shared.models import Document, SearchRequest
import logging

class LibraryHoldingsAdapter(BaseRetriever):
    """연세대학교 도서관 소장자료(단행본 등) 어댑터"""
    
    def __init__(self):
        self.scraper = LibraryHoldingsScraper(
            user_id=settings.YONSEI_ID,
            user_pw=settings.YONSEI_PW
        )
        self.logger = logging.getLogger(__name__)
    
    async def search(
        self, 
        request: SearchRequest,
        top_k: int = 10
    ) -> List[Document]:
        """
        도서관 소장자료 검색 결과를 표준 Document 형식으로 변환
        """
        try:
            # SearchRequest에서 첫 번째 쿼리 사용 (multi-query는 RetrieverService에서 처리)
            query_text = request.queries[0][0] if request.queries else request.user_query
            
            # 필터 처리
            search_params_dict = {
                "query": query_text,
                "results_per_page": 50 if top_k > 20 else 20 # 적절한 페이지 사이즈 선택
            }
            
            if request.filters:
                if "year_range" in request.filters:
                    from_year, to_year = request.filters["year_range"]
                    search_params_dict["year_range"] = YearRange(from_year=from_year, to_year=to_year)
                
                if "search_field" in request.filters:
                    try:
                        search_params_dict["search_field"] = LibrarySearchField(request.filters["search_field"])
                    except ValueError:
                        pass
                
                if "material_types" in request.filters:
                    # 문자열 리스트를 Enum 리스트로 변환
                    types = []
                    for t in request.filters["material_types"]:
                        try:
                            types.append(HoldingsMaterialType(t))
                        except ValueError:
                            pass
                    if types:
                        search_params_dict["material_types"] = types

            params = LibraryHoldingsSearchParams(**search_params_dict)

            # 스크래퍼 호출
            async with self.scraper as scraper:
                raw_results = await scraper.execute_holdings_search(
                    params=params,
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
    
    def _extract_text(self, item) -> str:
        """스크래핑 결과에서 검색 가능한 텍스트 추출"""
        # item is LibraryHoldingInfo
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
            await self.search("test", top_k=1)
            return True
        except:
            return False
    
    @property
    def source_name(self) -> str:
        return "yonsei_holdings"
