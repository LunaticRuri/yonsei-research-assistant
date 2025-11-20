import asyncio
from bs4 import BeautifulSoup
from enum import Enum
import logging
import os
from pydantic import BaseModel, Field, field_validator
import re
import sys
from typing import List, Optional, Literal
from urllib.parse import quote

# 현재 파일의 위치를 기준으로 프로젝트 루트(yonsei-research-assistant) 경로를 찾아 sys.path에 추가
# 현재위치(search) -> 상위(retrieval-service) -> 상위(backend)
current_dir = os.path.dirname(os.path.abspath(__file__))
service_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(service_root)

from shared.models import ElectronicResourceInfo
from base_scraper import BaseLibraryScraper
from urllib.parse import urljoin, urlparse, parse_qs, unquote

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Electronic Resource Search Parameters
# ============================================================================

class SearchField(str, Enum):
    """검색 필드 타입 (전자자료용)"""
    KEYWORD = "TX"  # 키워드
    TOTAL = ""      # 전체
    TITLE = "TI"     # 제목
    AUTHOR = "AU"    # 저자
    SUBJECT = "SU"  # 주제어


class QueryOperator(str, Enum):
    """검색 연산자"""
    AND = "and"
    OR = "or"
    NOT = "not"


class AdditionalQuery(BaseModel):
    """추가 검색 조건"""
    search_field: SearchField = Field(
        default=SearchField.TOTAL,
        description="검색할 필드 (키워드, 전체, 제목, 저자, 주제어)"
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


class ElectronicSearchParams(BaseModel):
    """전자자료 검색 파라미터
    
    Examples:
        # 간단한 검색
        >>> params = ElectronicSearchParams(
        ...     query="machine learning",
        ...     additional_queries=[
        ...         AdditionalQuery(query="deep learning", operator=QueryOperator.OR),
        ...         AdditionalQuery(query="reinforcement learning", operator=QueryOperator.OR)
        ...     ],
        ...     year_range=YearRange(from_year=2020, to_year=2025),
        ...     results_per_page=50
        ... )
        
        # 필드별 검색
        >>> params = ElectronicSearchParams(
        ...     query="artificial intelligence",
        ...     search_field=SearchField.TITLE,
        ...     additional_queries=[
        ...         AdditionalQuery(
        ...             search_field=SearchField.AUTHOR,
        ...             query="Hinton",
        ...             operator=QueryOperator.AND
        ...         )
        ...     ]
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
    year_range: Optional[YearRange] = Field(
        default=None,
        description="발행 연도 범위"
    )
    
    # 페이징 옵션
    results_per_page: Literal[10, 20, 30, 50, 100] = Field(
        default=20,
        description="페이지당 결과 수"
    )
    
    # 학술저널 필터 (기본값: True)
    academic_journals_only: bool = Field(
        default=True,
        description="학술저널만 검색할지 여부"
    )

    foreign_language: bool = Field(
        default=True,
        description="영어 등 외국어 자료도 검색할지 여부"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "machine learning",
                    "search_field": "TITLE",
                    "additional_queries": [
                        {
                            "search_field": "AUTHOR",
                            "query": "Hinton",
                            "operator": "AND"
                        },
                        {
                            "search_field": "SUBJECT",
                            "query": "neural networks",
                            "operator": "AND"
                        }
                    ],
                    "year_range": {
                        "from_year": 2020,
                        "to_year": 2025
                    },
                    "results_per_page": 50,
                    "academic_journals_only": True,
                    "foreign_language": False
                }
            ]
        }
    }


class ElectronicResourceScraper(BaseLibraryScraper):
    """전자자료(학술논문, E-Journal 등) 전용 스크래퍼"""

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

    async def execute_electronic_search(
        self, 
        params: ElectronicSearchParams,
        max_results: int = 20
    ) -> List[ElectronicResourceInfo]:
        """
        전자자료 검색 실행
        
        Args:
            params: ElectronicSearchParams 객체로 구조화된 검색 파라미터
            max_results: 최대 결과 수
        
        Returns:
            전자자료 검색 결과 리스트
        """
        try:
            # URL 생성 (전자자료 전용 로직)
            search_url = self._build_electronic_search_url(params, page=1)
            logger.info(f"Executing electronic resource search: {search_url}")
            
            # 공통 메서드로 요청
            html_content = await self._fetch(search_url)
            
            await asyncio.sleep(self.request_delay)
            
            # 검색 결과 파싱 (페이징 자동 처리)
            search_results = await self._parse_electronic_search_results(
                html_content,
                max_results, # 페이징을 위한 파라미터 전달
                params
                )
            logger.info(f"Final result count: {len(search_results)} (requested: {max_results})")
            
            logger.debug(search_results)
        
            # 각 결과에 대해 상세 정보 수집
            detailed_results = []
            for result in search_results:
                try:
                    detailed_info = await self._get_electronic_detailed_info(result)
                    detailed_results.append(detailed_info)
                    
                    # 요청 간 지연
                    await asyncio.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.warning(f"Failed to get detailed info for {result.get('title', 'Unknown')}: {e}")
                    detailed_results.append(result)  # 기본 정보로 대체
            return detailed_results
        
        except Exception as e:
            logger.error(f"Electronic resource search failed: {e}")
            raise

    def _build_electronic_search_url(self, params: ElectronicSearchParams, page: int) -> str:
        """
        전자자료 검색 URL 구성 (EDS - EBSCO Discovery Service)
        
        Args:
            params: ElectronicSearchParams 객체로 구조화된 검색 파라미터
            page: 페이지 번호 (1부터 시작)
        
        Returns:
            str: 구성된 검색 URL
        """
        # EDS 검색 엔드포인트
        endpoint = "/eds/brief/discoveryResult"
        
        # 기본 검색 파라미터 구성 (순서 중요)
        url_params = []
        
        # 필수 파라미터 (순서 중요)
        url_params.append(('commandType', 'advanced'))
        url_params.append(('st', 'KWRD'))
        url_params.append(('mId', ''))
        
        # 첫 번째 검색어 (주 검색어)
        # 순서: si -> q (주의: si가 먼저!)
        eds_field = params.search_field.value
        url_params.append(('si', eds_field))  # 빈 문자열은 전체 검색
        url_params.append(('q', params.query))
        
        # 추가 검색어가 있는 경우
        if params.additional_queries:
            for idx, add_query in enumerate(params.additional_queries):
                # 순서: b{N} -> weight{N} -> si -> q
                url_params.append((f'b{idx}', add_query.operator.value))
                url_params.append((f'weight{idx}', ''))
                
                # 추가 검색어의 필드 매핑
                add_eds_field = add_query.search_field.value
                url_params.append(('si', add_eds_field))
                url_params.append(('q', add_query.query))
            
            # 마지막 weight 파라미터 (다음 검색어 대비)
            last_weight_idx = len(params.additional_queries)
            url_params.append((f'weight{last_weight_idx}', ''))
        
        # 전자자료 필터 옵션
        url_params.append(('_fullTextYn', 'on'))      # Full Text 가능한 자료만
        # url_params.append(('_peerReviewedYn', 'on'))  # 동료심사(Peer Reviewed) 자료만
        
        # 발행년도 범위 설정 (빈 문자열로도 포함)
        url_params.append(('bk_rf', str(params.year_range.from_year) if params.year_range and params.year_range.from_year else ''))
        url_params.append(('bk_rt', str(params.year_range.to_year) if params.year_range and params.year_range.to_year else ''))
        
        # 필터 옵션: 학술저널만 or 한국어 자료만 검색 시 isRefine=Y 추가
        if params.academic_journals_only or not params.foreign_language:
            url_params.append(('isRefine', 'Y'))

        # Facet 필터: 학술저널만 검색 (옵션)
        if params.academic_journals_only:
            url_params.append(('edsFacetValue', 'SourceType:Academic Journals'))
        
        # Facet 필터: 한국어 자료만 검색 (옵션)
        if not params.foreign_language:
            url_params.append(('edsFacetValue', 'Language:한국어'))
            url_params.append(('edsFacetValue', 'Language:korean'))
        
        # 페이징 설정
        url_params.append(('pn', str(page)))
        url_params.append(('cpp', str(params.results_per_page)))
        
        param_string = "&".join([f"{k}={quote(str(v))}" for k, v in url_params])
        
        return f"{self.base_url}{endpoint}?{param_string}"

    async def _parse_electronic_search_results(
            self,
            html_content: str, 
            max_result: int, 
            params: Optional[ElectronicResourceInfo] = None
            ) -> list:
        """
        전자자료 검색 결과 파싱
        
        Args:
            html_content: 검색 결과 HTML 내용
            max_results: 반환할 최대 결과 수
            params: ElectronicSearchParams 객체 (페이징용)
            
        Returns:
            전자자료 검색 결과 리스트 (각 항목의 access_id 포함)
        """

        results = []
        current_page = 1
        current_html = html_content
        total_results_available = None
        
        while len(results) < max_result:
            soup = BeautifulSoup(current_html, 'html.parser')
            
            # 첫 페이지에서 전체 검색 결과 수 추출
            if current_page == 1 and total_results_available is None:
                search_cnt = soup.select_one('p.searchCnt span')    
                if search_cnt:
                    try:
                        # "총 10,271건 "에서 숫자 추출
                        total_results_available = int(search_cnt.get_text(strip=True).replace(',',''))
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
                    # 예: id="item_edsker_edsker.000005184827" -> "edsker_edsker.000005184827"
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
            next_url = self._build_electronic_search_url(params, page=current_page)
            
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
    
    async def _get_electronic_detailed_info(self, access_id: str) -> ElectronicResourceInfo:
        """전자자료 상세 정보 페이지에서 추가 정보 추출 (초록, 키워드 등)"""

        # 기본값으로 초기화
        access_id = access_id
        title = ""
        author = []
        source = ""
        publication_year = 0
        doi = ""
        link_url = ""
        abstract = ""
        keywords = []
        detail_url = f"{self.base_url}/eds/detail/{access_id}"

        try:
            session = await self._get_session()
            async with session.get(detail_url, timeout=15) as response:
                response.raise_for_status()
                html_content = await response.text()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 제목 추출 (profileHeader > h3)
            title_elem = soup.select_one('.profileHeader h3')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # 출처 추출 (profileHeader > p)
            source_elem = soup.select_one('.profileHeader p')
            if source_elem:
                source = source_elem.get_text(strip=True)
                # 발행년도 추출 및 추가
                try:
                    year = self._extract_year(source)
                    if year and year > 0:
                        publication_year = year
                        logger.debug(f"Found publication year for {access_id}: {year}")
                except Exception as e:
                    logger.debug(f"Failed to extract year from publication_info for {access_id}: {e}")
            
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
                    
                    if field_name == "저자":
                        # td 내부의 모든 <a> 태그 텍스트를 저자로 취급
                        a_tags = td.select('a')
                        if a_tags:
                            extracted_authors = []
                            for a in a_tags:
                                name = a.get_text(strip=True)
                                if name and name not in extracted_authors:
                                    extracted_authors.append(name)
                            author = extracted_authors
                        else:
                            author = [field_value]
                    
                    # 키워드 추출
                    if field_name == "키워드" or field_name == "주제어" or field_name == "MeSH Terms":
                        if field_name == "키워드" or field_name == "주제어":
                            # td 내부의 모든 <a> 태그 텍스트를 키워드로 취급
                            a_tags = td.select('a')
                            for a in a_tags:
                                kw = a.get_text(strip=True)
                                if kw and kw not in keywords:
                                    keywords.append(kw)
                        elif field_name == "MeSH Terms":
                            search_tags = td.select('searchlink')
                            for tag in search_tags:
                                kw = tag.get_text(strip=True)
                                if kw and kw not in keywords:
                                    keywords.append(kw)
                    
                    # 초록 추출
                    if field_name == "초록" or field_name == "Abstract":
                        abstract = field_value

                    # DOI 추출
                    if field_name == "DOI":
                        doi = field_value
            
            # Full Text 링크 추출
            try:
                online_ul = soup.select_one('ul.onlineAccess')
                if online_ul:
                    a_tag = online_ul.select_one('a') # 첫 번째 <a> 태그 선택
                    link_url = a_tag.get('href', '')
                else:
                    logger.debug("No onlineAccess section found for %s", access_id)
            except Exception as e:
                logger.debug("Failed to extract link_url for %s: %s", access_id, e)

            logger.info(f"Extracted info for {access_id}: {title}")
            
            # Pydantic 모델로 반환
            return ElectronicResourceInfo(
                access_id=access_id,
                title=title,
                author=author,
                source=source,
                publication_year=publication_year,
                doi=doi,
                link_url=link_url,
                abstract=abstract,
                keywords=keywords,
                detail_url=detail_url
            )
            
        except Exception as e:
            logger.warning(f"Failed to get detailed info for {access_id}: {e}")
            # 에러 발생 시 기본값으로 모델 반환
            return ElectronicResourceInfo(
                access_id=access_id,
                detail_url=detail_url
            )
   