import aiohttp
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Any, Optional, Literal
from urllib.parse import urljoin, quote
import asyncio
import re
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import sys
import os

# 현재 파일의 위치를 기준으로 프로젝트 루트(yonsei-research-assistant) 경로를 찾아 sys.path에 추가
# 현재위치(search) -> 상위(retrieval-service) -> 상위(backend)
current_dir = os.path.dirname(os.path.abspath(__file__))
service_root = os.path.abspath(os.path.join(current_dir, "../../")) # 2단계 상위로 이동
sys.path.append(service_root)

from shared.models import LibraryHoldingInfo, LibrarySearchField, HoldingsMaterialType
from base_scraper import BaseLibraryScraper
from search_params import BaseSearchParams, AdditionalQuery, YearRange

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Model for Library Search Parameters
# ============================================================================

class LibraryHoldingsSearchParams(BaseSearchParams):
    """도서관 검색 파라미터
    
    Examples:
        # 간단한 검색
        >>> params = LibraryHoldingsSearchParams(
        ...     query="휴대폰",
        ...     additional_queries=[
        ...         AdditionalQuery(search_field=LibrarySearchField.TOTAL, query="스마트폰", operator=QueryOperator.OR),
        ...         AdditionalQuery(search_field=LibrarySearchField.TOTAL, query="아이폰", operator=QueryOperator.NOT)
        ...     ],
        ...     year_range=YearRange(from_year=2020, to_year=2025),
        ...     results_per_page=100
        ... )
        
        # 필드별 검색
        >>> params = LibraryHoldingsSearchParams(
        ...     query="휴대폰",
        ...     search_field=LibrarySearchField.TITLE,
        ...     additional_queries=[
        ...         AdditionalQuery(
        ...             search_field=LibrarySearchField.AUTHOR,
        ...             query="김철수",
        ...             operator=QueryOperator.AND
        ...         )
        ...     ]
        ... )
        
        # 자료 유형 선택
        >>> params = LibraryHoldingsSearchParams(
        ...     query="휴대폰",
        ...     material_types=[MaterialType.SERIAL, MaterialType.THESIS]
        ... )
    """
    
    # 검색 옵션 (도서관 소장자료 전용)
    search_field: LibrarySearchField = Field(
        default=LibrarySearchField.TOTAL,
        description="주 검색어의 검색 필드"
    )
    
    # 추가 검색 조건 (도서관 소장자료 전용 필드 사용)
    additional_queries: List[AdditionalQuery[LibrarySearchField]] = Field(
        default_factory=list,
        max_length=10,
        description="추가 검색 조건 (최대 10개)"
    )
    
    # 연도 범위 필터
    year_range: Optional[YearRange] = Field(
        default=None,
        description="발행 연도 범위"
    )

    # 필터링 옵션 (도서관 소장자료만)
    material_types: List[HoldingsMaterialType] = Field(
        default=[HoldingsMaterialType.TOTAL],
        min_length=1,
        description="검색할 자료 유형 (여러 개 선택 가능)"
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


class LibraryHoldingsScraper(BaseLibraryScraper):
    """연세대학교 도서관 소장자료(단행본 등) 스크래핑"""
    
    def __init__(self, user_id: str = None, user_pw: str = None):
        super().__init__()
        self.user_id = user_id
        self.user_pw = user_pw
        self.is_logged_in = False
    
    async def __aenter__(self):
        """
        async with 구문에 진입할 때 호출됨.
        여기서 세션을 열고 + 로그인을 수행함.
        """
        # 1. 부모의 __aenter__ 호출 (세션 생성)
        await super().__aenter__()
        
        # 2. 아이디/비번이 있으면 로그인 시도
        if self.user_id and self.user_pw:
            success = await self.perform_login(self.user_id, self.user_pw)
            if not success:
                logger.error("Auto-login failed during initialization.")
                raise Exception("Login Failed") # 로그인이 필수라면 여기서 에러를 발생시켜서 진행을 막을 수 있음
            else:
                self.is_logged_in = True
        
        return self
    
    async def execute_holdings_search(
        self, 
        params: LibraryHoldingsSearchParams,
        max_results: int = 20
    ) -> List[LibraryHoldingInfo]:
        """
        도서관 통합검색 실행 (Pydantic 기반 인터페이스)
        
        페이지네이션을 자동으로 처리하여 max_results만큼의 결과를 수집합니다.
        _parse_holdings_search_results가 내부적으로 페이징을 처리합니다.
        
        Args:
            params: LibrarySearchParams 객체로 구조화된 검색 파라미터
            max_results: 최대 결과 수 (페이지네이션 자동 처리)
        
        Returns:
            검색 결과 리스트 (access_id 포함)
        
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
            session = await self._get_session()
            
            # 검색 URL 구성 (첫 페이지)
            search_url = self._build_holdings_search_url(params, page=1)
            
            logger.info(f"Executing holdings search: {search_url}")
            
            # 검색 요청
            async with session.get(search_url, timeout=30) as response:
                response.raise_for_status()
                html_content = await response.text()
            
            # 윤리적 지연
            await asyncio.sleep(self.request_delay)
            
            # 검색 결과 파싱 (페이징 자동 처리)
            search_results = await self._parse_holdings_search_results(
                html_content,
                max_result=max_results,
                params=params  # 페이징을 위한 파라미터 전달
            )
            
            logger.info(f"Final result count: {len(search_results)} (requested: {max_results})")
            
            logger.debug(search_results)
        
            # 각 결과에 대해 상세 정보 수집
            detailed_results = []
            for result in search_results:
                try:
                    detailed_info = await self._get_holdings_detailed_info(result)
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
    
    def _build_holdings_search_url(self, params: LibraryHoldingsSearchParams, page: int = 1) -> str:
        """
        검색 URL 구성 (Pydantic 기반)
        
        Args:
            params: LibrarySearchParams 객체로 구조화된 검색 파라미터
            page: 페이지 번호 (1부터 시작)
        
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
            >>> url = scraper._build_holdings_search_url(params, page=2)
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
        
        url_params.append(('oi', 'DISP06'))  # 정렬 기준 (출력순서: 출판년)
        url_params.append(('os', 'DESC'))  # 정렬 방식 (내림차순)

        # 페이징 설정
        url_params.append(('pn', str(page)))  # 페이지 번호 (1부터 시작)
        url_params.append(('cpp', str(params.results_per_page)))  # 쪽당 출력 건수
        url_params.append(('msc', '1000'))  # 최대 검색 건수
        
        # URL 파라미터 문자열 구성
        param_string = "&".join([f"{k}={quote(str(v))}" for k, v in url_params])
        
        return f"{self.base_url}{endpoint}?{param_string}"
    
    async def _parse_holdings_search_results(
        self,
        html_content: str,
        max_result: int = 100,
        params: Optional[LibraryHoldingsSearchParams] = None
    ) -> list:
        """
        검색 결과 파싱 - 페이징을 자동으로 처리하여 max_result만큼 결과를 수집
        
        Args:
            html_content: 첫 페이지의 검색 결과 HTML 내용
            search_type: 검색 유형
            max_result: 반환할 최대 결과 수
            params: 페이징을 위한 검색 파라미터 (None이면 첫 페이지만 파싱)
            
        Returns:
            검색 결과 리스트 (각 항목에 access_id 포함)
        """
        
        results = []
        current_page = 1
        current_html = html_content
        total_results_available = None
        
        while len(results) < max_result:
            soup = BeautifulSoup(current_html, 'html.parser')
            
            # 첫 페이지에서 전체 검색 결과 수 추출
            if current_page == 1 and total_results_available is None:
                search_cnt_list = soup.select('p.searchCnt strong')    
                if search_cnt_list:
                    try:
                        # "총 271건 중 271건 출력"에서 두 번째 숫자 추출
                        total_results_available = int(search_cnt_list[1].get_text(strip=True).replace(',',''))
                        logger.info(f"Total results available: {total_results_available}")
                        
                        # 실제 가져올 수 있는 결과 수로 max_result 조정
                        if total_results_available < max_result:
                            logger.info(f"Adjusting max_result from {max_result} to {total_results_available}")
                            max_result = total_results_available
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Failed to parse total result count: {e}")
            
            # 검색 결과 항목 찾기 - <li class="items"> 선택
            result_items = soup.select('ul.resultList li.items')
            
            logger.info(f"Found {len(result_items)} result items on page {current_page}")
            
            # 현재 페이지에 결과가 없으면 중단
            if not result_items:
                logger.info(f"No more results found on page {current_page}")
                break
            
            # 현재 페이지의 결과 수집
            page_results_count = 0
            for item in result_items:
                try:
                    # 각 li 항목의 id 속성에서 접근 ID 추출
                    # 예: id="item_CATTOT000002202406" -> "CATTOT000002202406"
                    item_id = item.get('id', '')
                    if item_id.startswith('item_'):
                        access_id = item_id.replace('item_', '')
                    else:
                        # id 속성이 없는 경우, checkbox value에서 추출
                        checkbox = item.select_one('input[type="checkbox"][name="data"]')
                        if checkbox:
                            access_id = checkbox.get('value', '')
                        else:
                            logger.warning(f"Could not find access ID for item")
                            continue
                    
                    results.append(access_id)
                    page_results_count += 1
                        
                    # max_result 제한 체크
                    if len(results) >= max_result:
                        logger.info(f"Reached max_result limit: {max_result}")
                        break
                            
                except Exception as e:
                    logger.warning(f"Failed to parse result item: {e}")
                    continue
            
            logger.info(f"Collected {page_results_count} results from page {current_page}. Total: {len(results)}/{max_result}")
            
            # max_result에 도달했거나 params가 없으면 중단
            if len(results) >= max_result or params is None:
                break
            
            # 다음 페이지 가져오기
            current_page += 1
            next_url = self._build_holdings_search_url(params, page=current_page)
            
            logger.info(f"Fetching next page {current_page}: {next_url}")
            
            try:
                # 윤리적 지연
                await asyncio.sleep(self.request_delay)
                
                session = await self._get_session()
                async with session.get(next_url, timeout=30) as response:
                    response.raise_for_status()
                    current_html = await response.text()
                
            except Exception as e:
                logger.error(f"Failed to fetch page {current_page}: {e}")
                break
        
        return results
    
    async def _get_holdings_detailed_info(self, access_id: str) -> LibraryHoldingInfo:
        """검색 결과의 상세 정보 조회"""
        
        url = f"{self.base_url}/search/detail/{access_id}"
        
        # 기본값으로 초기화
        title = ""
        author = ""
        material_type = ""
        publication_info = ""
        publication_year = 0
        isbn = ""
        book_description = ""

        try:
            session = await self._get_session()
            async with session.get(url, timeout=15) as response:
                response.raise_for_status()
                html_content = await response.text()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 제목 추출 (profileHeader > h3)
            title_elem = soup.select_one('.profileHeader h3')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # 저자 추출 (profileHeader > p)
            author_elem = soup.select_one('.profileHeader p')
            if author_elem:
                author = author_elem.get_text(strip=True)
            
            # 상세 정보 테이블에서 추출
            detail_table = soup.select_one('table#moreInfo')
            if detail_table:
                rows = detail_table.select('tr')
                for row in rows:
                    th = row.select_one('th')
                    td = row.select_one('td')
                    
                    if not th or not td:
                        continue
                    
                    field_name = th.get_text(strip=True)
                    field_value = td.get_text(strip=True)
                    
                    # 자료유형 추출
                    if field_name == "자료유형":
                        material_type = field_value
                    
                    # 발행사항 추출
                    elif field_name == "발행사항":
                        publication_info = field_value
                        # 발행년도 추출 및 추가
                        try:
                            year = self._extract_year(field_value)
                            if year and year > 0:
                                publication_year = year
                                logger.debug(f"Found publication year for {access_id}: {year}")
                        except Exception as e:
                            logger.debug(f"Failed to extract year from publication_info for {access_id}: {e}")
                    
                    # ISBN 추출
                    elif field_name == "ISBN":
                        isbn = field_value
            
            # 책 소개 추출
            descriptions = []
            
            # 모든 책 소개 섹션 찾기 (일반 책소개 + 출판사 제공 책소개)
            book_intro_sections = soup.select('.searchInfo.mediaContents')
            
            for section in book_intro_sections:
                # 먼저 전체 소개 (full) 찾기
                full_description = section.select_one('.mediaContent div.full')
                if full_description:
                    # <br> 태그를 줄바꿈으로 변환
                    for br in full_description.find_all('br'):
                        br.replace_with('\n')
                    desc_text = full_description.get_text(strip=True)
                    if desc_text:
                        descriptions.append(desc_text)
                else:
                    # full이 없으면 일반 p 태그나 brief 찾기
                    description_elem = section.select_one('.mediaContent p, .mediaContent div.brief')
                    if description_elem:
                        # <br> 태그를 줄바꿈으로 변환
                        for br in description_elem.find_all('br'):
                            br.replace_with('\n')
                        desc_text = description_elem.get_text(strip=True)
                        if desc_text:
                            descriptions.append(desc_text)
            
            # 모든 설명을 하나로 합치기 (중복 제거)
            if descriptions:
                # 중복된 설명 제거
                unique_descriptions = []
                for desc in descriptions:
                    if desc not in unique_descriptions:
                        unique_descriptions.append(desc)
                book_description = "\n\n".join(unique_descriptions)
            
            logger.info(f"Extracted info for {access_id}: {title}")
            
            # Pydantic 모델로 반환
            return LibraryHoldingInfo(
                access_id=access_id,
                title=title,
                author=author,
                material_type=material_type,
                publication_info=publication_info,
                publication_year=publication_year,
                isbn=isbn,
                book_description=book_description,
                detail_url=url
            )
            
        except Exception as e:
            logger.warning(f"Failed to get detailed info for {access_id}: {e}")
            # 에러 발생 시 기본값으로 모델 반환
            return LibraryHoldingInfo(
                access_id=access_id,
                title="",
                author="",
                material_type="",
                publication_info="",
                publication_year=0,
                isbn="",
                book_description="",
                detail_url=url
            )
    
    def _extract_year(self, text: str) -> int:
        """텍스트에서 연도 추출"""
        
        # 4자리 연도 패턴 찾기 (숫자가 아닌 문자로 둘러싸인 19xx 또는 20xx)
        # 예: "2023", "c2023", "(2023)", "2023." 등
        year_pattern = r'(?<!\d)(?:19|20)\d{2}(?!\d)'
        matches = re.findall(year_pattern, text)
        
        if matches:
            # 가장 최근 연도 반환
            return max(map(int, matches))
        
        return 0