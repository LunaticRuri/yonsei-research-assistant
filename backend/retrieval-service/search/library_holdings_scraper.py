import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Any, Optional, Literal
from urllib.parse import urljoin, quote
import asyncio
import aiohttp
from pydantic import BaseModel, Field, field_validator
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Library Search Parameters
# ============================================================================

class SearchField(str, Enum):
    """검색 필드 타입"""
    TOTAL = "TOTAL"  # 전체
    TITLE = "1"  # 서명(책제목)
    AUTHOR = "2"  # 저자
    PUBLISHER = "3"  # 출판사
    SUBJECT = "4"  # 주제어


class MaterialType(str, Enum):
    """자료 유형"""
    TOTAL = "TOTAL"  # 전체
    BOOK = "m"  # 단행본
    SERIAL = "s"  # 연속간행물
    MULTIMEDIA = "b;p;v;x;u;c"  # 멀티미디어/비도서
    THESIS = "t"  # 학위논문
    OLD_BOOK = "o"  # 고서
    ARTICLE = "zart"  # 기사


class QueryOperator(str, Enum):
    """검색 연산자"""
    AND = "and"
    OR = "or"
    NOT = "not"


class AdditionalQuery(BaseModel):
    """추가 검색 조건"""
    search_field: SearchField = Field(
        default=SearchField.TOTAL,
        description="검색할 필드 (전체, 서명, 저자, 출판사, 주제어)"
    )
    query: str = Field(
        ...,
        min_length=1,
        description="검색어"
    )
    operator: QueryOperator = Field(
        default=QueryOperator.AND,
        description="이전 검색어와의 연산자 (AND, OR, NOT)"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "search_field": "AUTHOR",
                    "query": "김철수",
                    "operator": "AND"
                }
            ]
        }
    }


class YearRange(BaseModel):
    """발행 연도 범위"""
    from_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="시작 연도"
    )
    to_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="종료 연도"
    )
    
    @field_validator('to_year')
    @classmethod
    def validate_year_range(cls, v, info):
        """종료 연도가 시작 연도보다 크거나 같은지 검증"""
        if v is not None and info.data.get('from_year') is not None:
            if v < info.data['from_year']:
                raise ValueError('종료 연도는 시작 연도보다 크거나 같아야 합니다')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"from_year": 2020, "to_year": 2025}
            ]
        }
    }


class LibraryHoldingsSearchParams(BaseModel):
    """도서관 검색 파라미터
    
    Examples:
        # 간단한 검색
        >>> params = LibrarySearchParams(
        ...     query="휴대폰",
        ...     additional_queries=[
        ...         AdditionalQuery(query="스마트폰", operator=QueryOperator.OR),
        ...         AdditionalQuery(query="아이폰", operator=QueryOperator.NOT)
        ...     ],
        ...     year_range=YearRange(from_year=2020, to_year=2025),
        ...     results_per_page=100
        ... )
        
        # 필드별 검색
        >>> params = LibrarySearchParams(
        ...     query="휴대폰",
        ...     search_field=SearchField.TITLE,
        ...     additional_queries=[
        ...         AdditionalQuery(
        ...             search_field=SearchField.AUTHOR,
        ...             query="김철수",
        ...             operator=QueryOperator.AND
        ...         )
        ...     ]
        ... )
        
        # 자료 유형 선택
        >>> params = LibrarySearchParams(
        ...     query="휴대폰",
        ...     material_types=[MaterialType.SERIAL, MaterialType.THESIS]
        ... )
    """
    
    # 필수 파라미터
    query: str = Field(
        ...,
        min_length=1,
        description="주 검색어"
    )
    
    # 검색 옵션
    search_field: SearchField = Field(
        default=SearchField.TOTAL,
        description="주 검색어의 검색 필드"
    )
    
    # 추가 검색 조건
    additional_queries: List[AdditionalQuery] = Field(
        default_factory=list,
        max_length=10,
        description="추가 검색 조건 (최대 10개)"
    )
    
    # 필터링 옵션
    material_types: List[MaterialType] = Field(
        default=[MaterialType.TOTAL],
        min_length=1,
        description="검색할 자료 유형 (여러 개 선택 가능)"
    )
    
    year_range: Optional[YearRange] = Field(
        default=None,
        description="발행 연도 범위"
    )
    
    # 페이징 옵션
    results_per_page: Literal[5, 10, 15, 20, 30, 50, 100] = Field(
        default=10,
        description="페이지당 결과 수"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "휴대폰",
                    "search_field": "TITLE",
                    "additional_queries": [
                        {
                            "search_field": "AUTHOR",
                            "query": "김철수",
                            "operator": "AND"
                        },
                        {
                            "search_field": "SUBJECT",
                            "query": "아이폰",
                            "operator": "AND"
                        }
                    ],
                    "material_types": ["SERIAL", "THESIS"],
                    "year_range": {
                        "from_year": 2020,
                        "to_year": 2025
                    },
                    "results_per_page": 100
                }
            ]
        }
    }


class LibraryHoldingsScraper:
    """연세대학교 도서관 웹사이트 스크래핑"""
    
    def __init__(self):
        self.base_url = "https://library.yonsei.ac.kr"
        
        # 요청 간격 (윤리적 스크래핑)
        self.request_delay = 0.5
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br'
        })
    
    async def execute_holdings_search(
        self, 
        params: LibraryHoldingsSearchParams,
        search_type: str = "integrated",
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        도서관 통합검색 실행 (Pydantic 기반 인터페이스)
        
        Args:
            params: LibrarySearchParams 객체로 구조화된 검색 파라미터
            search_type: 검색 유형 (integrated, books, articles, thesis)
            max_results: 최대 결과 수
        
        Returns:
            검색 결과 리스트
        
        Examples:
            # 간단한 검색
            >>> params = LibrarySearchParams(
            ...     query="휴대폰",
            ...     additional_queries=[
            ...         AdditionalQuery(query="스마트폰", operator=QueryOperator.OR),
            ...         AdditionalQuery(query="아이폰", operator=QueryOperator.NOT)
            ...     ],
            ...     year_range=YearRange(from_year=2020, to_year=2025),
            ...     results_per_page=100
            ... )
            >>> results = await scraper.execute_holdings_search(params)
            
            # 필드별 검색
            >>> params = LibrarySearchParams(
            ...     query="휴대폰",
            ...     search_field=SearchField.TITLE,
            ...     additional_queries=[
            ...         AdditionalQuery(
            ...             search_field=SearchField.AUTHOR,
            ...             query="김철수",
            ...             operator=QueryOperator.AND
            ...         )
            ...     ]
            ... )
            >>> results = await scraper.execute_holdings_search(params)
            
            # 자료 유형 선택
            >>> params = LibrarySearchParams(
            ...     query="휴대폰",
            ...     material_types=[MaterialType.SERIAL, MaterialType.THESIS]
            ... )
            >>> results = await scraper.execute_holdings_search(params)
        """
        
        try:
            # 검색 URL 구성
            search_url = self._build_holdings_search_url(params)
            
            logger.info(f"Executing holdings search: {search_url}")
            
            # 검색 요청
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            # 윤리적 지연
            await asyncio.sleep(self.request_delay)
            
            # 결과 파싱
            search_results = self._parse_holdings_search_results(response.text, search_type)
            
            # 최대 결과 수 제한
            limited_results = search_results[:max_results]
            
            # 각 결과에 대해 상세 정보 수집
            detailed_results = []
            for result in limited_results:
                try:
                    detailed_info = await self._get_detailed_info(result)
                    detailed_results.append(detailed_info)
                    
                    # 요청 간 지연
                    await asyncio.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.warning(f"Failed to get detailed info for {result.get('title', 'Unknown')}: {e}")
                    detailed_results.append(result)
            
            return detailed_results
            
        except Exception as e:
            logger.error(f"Library search failed: {e}")
            raise
    
    def _build_holdings_search_url(self, params: LibraryHoldingsSearchParams) -> str:
        """
        검색 URL 구성 (Pydantic 기반)
        
        Args:
            params: LibrarySearchParams 객체로 구조화된 검색 파라미터
        
        Returns:
            str: 구성된 검색 URL
        
        Examples:
            >>> params = LibrarySearchParams(
            ...     query="휴대폰",
            ...     search_field=SearchField.TITLE,
            ...     additional_queries=[
            ...         AdditionalQuery(search_field=SearchField.AUTHOR, query="김철수")
            ...     ],
            ...     material_types=[MaterialType.SERIAL, MaterialType.THESIS],
            ...     year_range=YearRange(from_year=2020, to_year=2025),
            ...     results_per_page=100
            ... )
            >>> url = scraper._build_holdings_search_url(params)
        """
        
        # 통합검색 결과 페이지 엔드포인트
        endpoint = "/search/tot/result"
        
        # 기본 검색 파라미터 구성 (순서 중요)
        url_params = []
        
        # 필수 파라미터
        url_params.append(('st', 'KWRD'))
        url_params.append(('commandType', 'advanced'))
        
        # 첫 번째 검색어 (주 검색어)
        url_params.append(('si', params.search_field.value))
        url_params.append(('q', params.query))
        
        # 추가 검색어가 있는 경우 (AND/OR/NOT 연산)
        if params.additional_queries:
            for idx, add_query in enumerate(params.additional_queries):
                url_params.append((f'b{idx}', add_query.operator.value))
                url_params.append((f'weight{idx}', ''))
                url_params.append(('si', add_query.search_field.value))
                url_params.append(('q', add_query.query))
            
            # 마지막 weight 파라미터
            last_weight_idx = len(params.additional_queries)
            url_params.append((f'weight{last_weight_idx}', ''))
        
        # 자료유형 파라미터
        material_type_values = [mt.value for mt in params.material_types]
        material_type_order = ['TOTAL', 'm', 's', 'b;p;v;x;u;c', 't', 'o', 'zart']
        
        # 첫 번째 _lmt0 (항상 on)
        url_params.append(('_lmt0', 'on'))
        url_params.append(('lmtsn', '000000000001'))
        url_params.append(('lmtst', 'OR'))
        
        # 선택된 자료유형에 따라 파라미터 추가
        for mat_type in material_type_order:
            url_params.append(('_lmt0', 'on'))
            if mat_type in material_type_values:
                url_params.append(('lmt0', mat_type))
        
        # 수록매체 제한 (inc)
        url_params.append(('inc', 'TOTAL'))
        for _ in range(6):
            url_params.append(('_inc', 'on'))
        
        # 언어 제한 (lmt1)
        url_params.append(('lmt1', 'TOTAL'))
        url_params.append(('lmtsn', '000000000003'))
        url_params.append(('lmtst', 'OR'))
        
        # 소장처 제한 (lmt2) - 신촌+국제
        url_params.append(('lmt2', 'YNLIB;GSISL;MUSEL;OTHER;UGSTL;YSLIB;ARCHL;BUSIL;KORCL;IOKSL;LAWSL;MULTL;MATHL;MUSIC;UML'))
        url_params.append(('lmtsn', '000000000006'))
        url_params.append(('lmtst', 'OR'))
        
        # 발행년도 범위 설정
        if params.year_range:
            if params.year_range.from_year:
                url_params.append(('rf', str(params.year_range.from_year)))
            if params.year_range.to_year:
                url_params.append(('rt', str(params.year_range.to_year)))
            if params.year_range.from_year or params.year_range.to_year:
                url_params.append(('range', '000000000021'))
        
        # 페이징 설정
        url_params.append(('cpp', str(params.results_per_page)))  # 쪽당 출력 건수
        url_params.append(('msc', '10000'))  # 최대 검색 건수
        
        # URL 파라미터 문자열 구성
        param_string = "&".join([f"{k}={quote(str(v))}" for k, v in url_params])
        
        return f"{self.base_url}{endpoint}?{param_string}"
    
    def _parse_holdings_search_results(self, html_content: str, search_type: str) -> List[Dict[str, Any]]:
        """검색 결과 파싱"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        # 검색 결과 항목 선택자 (실제 HTML 구조에 따라 조정 필요)
        result_items = soup.select('.search-result-item, .list-item, .result-item')
        
        for item in result_items:
            try:
                result = self._extract_result_info(item, search_type)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to parse result item: {e}")
                continue
        
        return results
    
    def _extract_result_info(self, item_element, search_type: str) -> Optional[Dict[str, Any]]:
        """개별 검색 결과 정보 추출"""
        
        try:
            # 제목 추출
            title_elem = item_element.select_one('.title, .item-title, h3, h4')
            title = title_elem.get_text(strip=True) if title_elem else "제목 없음"
            
            # 저자 추출
            author_elem = item_element.select_one('.author, .item-author, .creator')
            authors = []
            if author_elem:
                author_text = author_elem.get_text(strip=True)
                authors = [author.strip() for author in author_text.split(',')]
            
            # 출판 정보 추출
            pub_elem = item_element.select_one('.publication, .pub-info, .publisher')
            publication_info = pub_elem.get_text(strip=True) if pub_elem else ""
            
            # 연도 추출
            year = self._extract_year(publication_info + " " + title)
            
            # 상세 링크 추출
            link_elem = item_element.select_one('a[href]')
            detail_link = ""
            if link_elem:
                href = link_elem.get('href')
                detail_link = urljoin(self.base_url, href) if href else ""
            
            # 자료 유형 추출
            type_elem = item_element.select_one('.type, .material-type, .format')
            material_type = type_elem.get_text(strip=True) if type_elem else "기타"
            
            return {
                "title": title,
                "authors": authors,
                "publication_info": publication_info,
                "year": year,
                "material_type": material_type,
                "detail_link": detail_link,
                "search_type": search_type
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract result info: {e}")
            return None
    
    async def _get_detailed_info(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """검색 결과의 상세 정보 조회"""
        
        if not result.get('detail_link'):
            return result
        
        try:
            response = self.session.get(result['detail_link'], timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 초록 추출
            abstract_elem = soup.select_one('.abstract, .summary, .description')
            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
            
            # 키워드 추출
            keywords_elem = soup.select_one('.keywords, .subjects, .tags')
            keywords = []
            if keywords_elem:
                keyword_text = keywords_elem.get_text(strip=True)
                keywords = [kw.strip() for kw in keyword_text.split(',')]
            
            # 소장 정보 추출
            holdings = self._extract_holdings_info(soup)
            
            # 원문 링크 추출
            fulltext_elem = soup.select_one('.fulltext-link, .pdf-link, .online-access')
            fulltext_link = ""
            if fulltext_elem:
                href = fulltext_elem.get('href')
                fulltext_link = urljoin(self.base_url, href) if href else ""
            
            # 기존 결과에 상세 정보 추가
            result.update({
                "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                "keywords": keywords,
                "holdings": holdings,
                "fulltext_link": fulltext_link
            })
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to get detailed info: {e}")
            return result
    
    async def _get_holdings_detail(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """소장 정보 상세 조회"""
        
        holdings = result.get('holdings', {})
        
        # 기본 소장 정보가 없으면 Mock 데이터 생성
        if not holdings:
            return self._generate_mock_holdings()
        
        return holdings
    
    def _extract_holdings_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """소장 정보 추출"""
        
        holdings = {
            "locations": [],
            "status": "available",
            "loan_status": "대출 가능",
            "access_type": "physical"
        }
        
        # 소장 위치 추출
        location_elems = soup.select('.location, .library-location, .holdings-location')
        for loc_elem in location_elems:
            location_text = loc_elem.get_text(strip=True)
            if location_text:
                holdings["locations"].append(location_text)
        
        # 대출 상태 추출
        status_elem = soup.select_one('.status, .availability, .loan-status')
        if status_elem:
            status_text = status_elem.get_text(strip=True)
            holdings["loan_status"] = status_text
            
            # 상태에 따른 가용성 판단
            if any(keyword in status_text for keyword in ["대출중", "이용불가", "분실"]):
                holdings["status"] = "unavailable"
        
        # 온라인 접근 여부 확인
        online_elem = soup.select_one('.online-access, .electronic-resource, .e-resource')
        if online_elem:
            holdings["access_type"] = "electronic"
            holdings["loan_status"] = "온라인 이용 가능"
        
        return holdings
    
    def _generate_access_info(self, holdings: Dict[str, Any]) -> str:
        """접근 정보 생성"""
        
        access_type = holdings.get("access_type", "physical")
        locations = holdings.get("locations", [])
        loan_status = holdings.get("loan_status", "")
        
        if access_type == "electronic":
            return "✅ 전자 저널 원문 이용 가능"
        elif locations:
            location_str = ", ".join(locations[:2])  # 최대 2개 위치만 표시
            return f"📚 {location_str} - {loan_status}"
        else:
            return f"📖 {loan_status}"
    
    def _generate_mock_holdings(self) -> Dict[str, Any]:
        """Mock 소장 정보 생성"""
        import random
        
        mock_locations = [
            "중앙도서관 3층",
            "학술정보원 2층", 
            "과학도서관 1층",
            "의학도서관"
        ]
        
        mock_statuses = [
            "대출 가능",
            "대출중",
            "온라인 이용 가능"
        ]
        
        return {
            "locations": [random.choice(mock_locations)],
            "status": "available",
            "loan_status": random.choice(mock_statuses),
            "access_type": random.choice(["physical", "electronic"])
        }
    
    def _extract_year(self, text: str) -> int:
        """텍스트에서 연도 추출"""
        import re
        
        # 4자리 연도 패턴 찾기
        year_pattern = r'\b(19|20)\d{2}\b'
        matches = re.findall(year_pattern, text)
        
        if matches:
            # 가장 최근 연도 반환
            years = [int(match + m[2:]) for match, m in re.findall(r'\b(19|20)(\d{2})\b', text)]
            return max(years) if years else 0
        
        return 0
    
    def __del__(self):
        """소멸자: 세션 정리"""
        if hasattr(self, 'session'):
            self.session.close()