from kiwipiepy import Kiwi
from typing import List
import logging

from retrieval_service.adapters.base_adapters import BaseRetriever
from retrieval_service.scrapers.library_holdings_scraper import LibraryHoldingsScraper, LibraryHoldingsSearchParams
from shared.models import (
    RetrievalRoute,
    Document,
    SearchRequest,
    LibrarySearchField,
    HoldingsMaterialType,
    LibraryHoldingInfo
)



class LibraryHoldingsAdapter(BaseRetriever):
    """연세대학교 도서관 소장자료(단행본 등) 어댑터"""
    
    def __init__(self):
        # NOTE: 아마 소장자료 검색은 로그인 쿠키가 없어도 될 듯
        # 혹시 요구되면 아래 줄 주석 해제
        # self.scraper = LibraryHoldingsScraper(user_id=settings.YONSEI_ID, user_pw=settings.YONSEI_PW)
        self.scraper = LibraryHoldingsScraper()
        self.logger = logging.getLogger(__name__)
        
        # NOTE: num_workers는 1로 해야 비동기 지원됨
        self.kiwi = Kiwi(num_workers=1)
    
    async def _filter_nouns(self, text: str) -> str:
        """한국어 텍스트에서 명사만 추출하여 반환"""
        nouns = []
        for token in self.kiwi.tokenize(text):
            if 'NN' in token.tag and 'NNB' not in token.tag:
                nouns.append(token.form)
        return " ".join(nouns)
    
    async def request_to_search_params(self, request: SearchRequest) -> LibraryHoldingsSearchParams:
        """
        SearchRequest를 LibraryHoldingsSearchParams 객체로 변환
        
        Args:
            request (SearchRequest): 통합 검색 요청 객체
        Returns:
            LibraryHoldingsSearchParams: 도서관 소장자료 어댑터용 검색 파라미터 객체
        """
        queries = request.queries
        filters = request.filters
        
        query = await self._filter_nouns(queries.query_1)
        search_field = queries.search_field_1 if isinstance(queries.search_field_1, LibrarySearchField) else LibrarySearchField.TOTAL
        year_range = None
        material_types = []

        additional_queries = []
        if queries.query_2:
            queries.query_2 = await self._filter_nouns(queries.query_2)
            if isinstance(queries.search_field_2, LibrarySearchField):
                search_field_2 = queries.search_field_2
            else:
                search_field_2 = LibrarySearchField.TOTAL
            
            additional_queries.append(
                {
                    "search_field": search_field_2,
                    "query": queries.query_2,
                    "operator": queries.operator_1
                }
            )

        if queries.query_3:
            queries.query_3 = await self._filter_nouns(queries.query_3)
            if isinstance(queries.search_field_3, LibrarySearchField):
                search_field_3 = queries.search_field_3
            else:
                search_field_3 = LibrarySearchField.TOTAL
            
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
        if filters.get("maraterial_types"):
            for t in filters["material_types"]:
                if isinstance(t, HoldingsMaterialType):
                    material_types.append(t)
                else:
                    try:
                        material_types.append(HoldingsMaterialType(t))
                    except ValueError:
                        pass
        
        if not material_types:
            material_types = [HoldingsMaterialType.TOTAL]
        
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
                        'source': RetrievalRoute.YONSEI_HOLDINGS.value,
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
