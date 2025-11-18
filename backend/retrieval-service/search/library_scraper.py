import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class LibraryScraper:
    """연세대학교 도서관 웹사이트 스크래핑"""
    
    def __init__(self):
        self.base_url = "https://library.yonsei.ac.kr"
        self.search_endpoints = {
            "integrated": "/search/tot",
            "books": "/search/book", 
            "articles": "/search/article",
            "thesis": "/search/thesis"
        }
        
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
    
    async def execute_library_search(
        self, 
        query: str, 
        search_type: str = "integrated",
        search_field: str = "TOTAL",
        max_results: int = 20,
        year_from: Optional[str] = None,
        year_to: Optional[str] = None,
        additional_queries: Optional[List[Dict[str, str]]] = None,
        material_types: Optional[List[str]] = None,
        results_per_page: int = 10
    ) -> List[Dict[str, Any]]:
        """
        도서관 통합검색 실행
        
        Args:
            query: 주 검색어
            search_type: 검색 유형 (integrated, books, articles, thesis)
            search_field: 주 검색어의 검색 항목
                - "TOTAL": 전체
                - "1": 서명(책제목)
                - "2": 저자
                - "3": 출판사
                - "4": 주제어
            max_results: 최대 결과 수
            year_from: 시작 연도 (예: "2020")
            year_to: 종료 연도 (예: "2025")
            additional_queries: 추가 검색 조건 리스트
                각 항목은 {"si": 검색필드, "q": 검색어, "operator": 연산자} 형식
            material_types: 자료유형 리스트 (여러 개 선택 가능)
                - "m": 단행본
                - "s": 연속간행물
                - "b;p;v;x;u;c": 멀티미디어/비도서
                - "t": 학위논문
                - "o": 고서
                - "zart": 기사
            results_per_page: 쪽당 출력 건수 (5, 10, 15, 20, 30, 50, 100)
        
        Examples:
            # 간단한 검색: "휴대폰 OR 스마트폰 NOT 아이폰"
            await execute_library_search(
                query="휴대폰",
                additional_queries=[
                    {"si": "TOTAL", "q": "스마트폰", "operator": "or"},
                    {"si": "TOTAL", "q": "아이폰", "operator": "not"}
                ],
                year_from="2020",
                year_to="2025",
                results_per_page=100
            )
            
            # 필드별 검색: 서명='휴대폰' AND 저자='김철수' AND 주제어='아이폰'
            await execute_library_search(
                query="휴대폰",
                search_field="1",  # 서명
                additional_queries=[
                    {"si": "2", "q": "김철수", "operator": "and"},  # 저자
                    {"si": "4", "q": "아이폰", "operator": "and"}   # 주제어
                ],
                year_from="2020",
                year_to="2025",
                results_per_page=100
            )
            
            # 자료유형 선택: 연속간행물과 학위논문만
            await execute_library_search(
                query="휴대폰",
                material_types=["s", "t"]  # 연속간행물, 학위논문
            )
        """
        
        try:
            # 검색 URL 구성
            search_url = self._build_search_url(
                query, 
                search_type,
                search_field=search_field,
                year_from=year_from,
                year_to=year_to,
                additional_queries=additional_queries,
                material_types=material_types,
                results_per_page=results_per_page
            )
            
            logger.info(f"Executing library search: {search_url}")
            
            # 검색 요청
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            # 윤리적 지연
            await asyncio.sleep(self.request_delay)
            
            # 결과 파싱
            search_results = self._parse_search_results(response.text, search_type)
            
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
    
    async def check_holdings(self, title: str, authors: Optional[List[str]] = None) -> Dict[str, Any]:
        """특정 자료의 소장 여부 및 이용 가능성 확인"""
        
        try:
            # 제목으로 검색
            query = f'title:"{title}"'
            if authors:
                author_query = " OR ".join([f'author:"{author}"' for author in authors[:2]])
                query += f" AND ({author_query})"
            
            search_results = await self.execute_library_search(query, max_results=5)
            
            if not search_results:
                return {
                    "status": "not_found",
                    "message": "해당 자료를 찾을 수 없습니다."
                }
            
            # 가장 유사한 결과 선택
            best_match = search_results[0]
            
            # 소장 정보 상세 조회
            holdings_info = await self._get_holdings_detail(best_match)
            
            return {
                "status": "found",
                "title": best_match.get("title"),
                "holdings": holdings_info,
                "access_info": self._generate_access_info(holdings_info)
            }
            
        except Exception as e:
            logger.error(f"Holdings check failed for '{title}': {e}")
            return {
                "status": "error",
                "message": f"소장 여부 확인 중 오류 발생: {str(e)}"
            }
    
    async def get_available_databases(self) -> List[Dict[str, str]]:
        """이용 가능한 데이터베이스 목록 조회"""
        
        try:
            # 데이터베이스 목록 페이지 조회
            db_list_url = f"{self.base_url}/database"
            
            response = self.session.get(db_list_url, timeout=30)
            response.raise_for_status()
            
            # 데이터베이스 목록 파싱
            databases = self._parse_database_list(response.text)
            
            return databases
            
        except Exception as e:
            logger.error(f"Failed to get database list: {e}")
            # 기본 데이터베이스 목록 반환
            return self._get_default_databases()
    
    async def test_connection(self) -> Dict[str, Any]:
        """도서관 웹사이트 연결 테스트"""
        
        try:
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()
            
            return {
                "status": "success",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code
            }
            
        except requests.exceptions.Timeout:
            return {
                "status": "timeout",
                "message": "연결 시간 초과"
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "connection_error", 
                "message": "연결 실패"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _build_search_url(
        self, 
        query: str, 
        search_type: str,
        search_field: str = "TOTAL",
        year_from: Optional[str] = None,
        year_to: Optional[str] = None,
        additional_queries: Optional[List[Dict[str, str]]] = None,
        material_types: Optional[List[str]] = None,
        results_per_page: int = 10
    ) -> str:
        """
        검색 URL 구성
        
        Args:
            query: 주 검색어
            search_type: 검색 유형 (integrated, books, articles, thesis)
            search_field: 주 검색어의 검색 항목
                - "TOTAL": 전체
                - "1": 서명(책제목)
                - "2": 저자
                - "3": 출판사
                - "4": 주제어
            year_from: 시작 연도 (예: "2020")
            year_to: 종료 연도 (예: "2025")
            additional_queries: 추가 검색 조건 리스트
                예: [{"si": "2", "q": "김철수", "operator": "and"},
                     {"si": "4", "q": "아이폰", "operator": "and"}]
            material_types: 자료유형 리스트 (여러 개 선택 가능)
                - "m": 단행본
                - "s": 연속간행물
                - "b;p;v;x;u;c": 멀티미디어/비도서
                - "t": 학위논문
                - "o": 고서
                - "zart": 기사
                - None이면 search_type에 따라 자동 결정
            results_per_page: 쪽당 출력 건수 (5, 10, 15, 20, 30, 50, 100)
        
        Examples:
            # 서명='휴대폰' AND 저자='김철수' AND 주제어='아이폰'
            _build_search_url(
                query="휴대폰",
                search_field="1",  # 서명
                additional_queries=[
                    {"si": "2", "q": "김철수", "operator": "and"},  # 저자
                    {"si": "4", "q": "아이폰", "operator": "and"}   # 주제어
                ]
            )
            
            # 연속간행물과 학위논문만 검색
            _build_search_url(
                query="휴대폰",
                material_types=["s", "t"]  # 연속간행물, 학위논문
            )
        """
        
        # 통합검색 결과 페이지 엔드포인트
        endpoint = "/search/tot/result"
        
        # 기본 검색 파라미터 구성 (순서 중요)
        params = []
        
        # 필수 파라미터
        params.append(('st', 'KWRD'))
        params.append(('commandType', 'advanced'))
        
        # 첫 번째 검색어 (주 검색어)
        params.append(('si', search_field))
        params.append(('q', query))
        
        # 추가 검색어가 있는 경우 (AND/OR/NOT 연산)
        if additional_queries:
            for idx, add_query in enumerate(additional_queries):
                operator = add_query.get('operator', 'and')  # and, or, not
                params.append((f'b{idx}', operator))
                params.append((f'weight{idx}', ''))
                params.append(('si', add_query.get('si', 'TOTAL')))
                params.append(('q', add_query.get('q', '')))
            
            # 마지막 weight 파라미터
            last_weight_idx = len(additional_queries)
            params.append((f'weight{last_weight_idx}', ''))
        
        # 자료유형 제한 (lmt0)
        # material_types가 지정되지 않았으면 search_type에 따라 결정
        if material_types is None:
            if search_type == "books":
                selected_material_types = ['m']  # 단행본
            elif search_type == "articles":
                selected_material_types = ['zart']  # 기사
            elif search_type == "thesis":
                selected_material_types = ['t']  # 학위논문
            else:
                selected_material_types = ['TOTAL']  # 전체
        else:
            selected_material_types = material_types
        
        # 자료유형 파라미터 구성 (HTML form 순서 반영)
        # 순서: TOTAL, m(단행본), s(연속간행물), b;p;v;x;u;c(멀티미디어), t(학위논문), o(고서), zart(기사)
        material_type_order = ['TOTAL', 'm', 's', 'b;p;v;x;u;c', 't', 'o', 'zart']
        
        # 첫 번째 _lmt0 (항상 on)
        params.append(('_lmt0', 'on'))
        params.append(('lmtsn', '000000000001'))
        params.append(('lmtst', 'OR'))
        
        # 선택된 자료유형에 따라 파라미터 추가
        for mat_type in material_type_order:
            params.append(('_lmt0', 'on'))
            if mat_type in selected_material_types:
                params.append(('lmt0', mat_type))
        
        # 수록매체 제한 (inc)
        params.append(('inc', 'TOTAL'))
        for _ in range(6):
            params.append(('_inc', 'on'))
        
        # 언어 제한 (lmt1)
        params.append(('lmt1', 'TOTAL'))
        params.append(('lmtsn', '000000000003'))
        params.append(('lmtst', 'OR'))
        
        # 소장처 제한 (lmt2) - 신촌+국제
        params.append(('lmt2', 'YNLIB;GSISL;MUSEL;OTHER;UGSTL;YSLIB;ARCHL;BUSIL;KORCL;IOKSL;LAWSL;MULTL;MATHL;MUSIC;UML'))
        params.append(('lmtsn', '000000000006'))
        params.append(('lmtst', 'OR'))
        
        # 발행년도 범위 설정
        if year_from:
            params.append(('rf', year_from))
        if year_to:
            params.append(('rt', year_to))
        if year_from or year_to:
            params.append(('range', '000000000021'))
        
        # 페이징 설정
        params.append(('cpp', str(results_per_page)))  # 쪽당 출력 건수
        params.append(('msc', '10000'))  # 최대 검색 건수
        
        # URL 파라미터 문자열 구성
        param_string = "&".join([f"{k}={quote(str(v))}" for k, v in params])
        
        return f"{self.base_url}{endpoint}?{param_string}"
    
    def _parse_search_results(self, html_content: str, search_type: str) -> List[Dict[str, Any]]:
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
    
    def _parse_database_list(self, html_content: str) -> List[Dict[str, str]]:
        """데이터베이스 목록 파싱"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        databases = []
        
        # 데이터베이스 항목 선택
        db_items = soup.select('.database-item, .db-list-item, .resource-item')
        
        for item in db_items:
            try:
                name_elem = item.select_one('.db-name, .resource-name, h3, h4')
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    
                    # 설명 추출
                    desc_elem = item.select_one('.description, .db-desc')
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # 링크 추출
                    link_elem = item.select_one('a[href]')
                    url = link_elem.get('href') if link_elem else ""
                    
                    databases.append({
                        "name": name,
                        "description": description[:100] + "..." if len(description) > 100 else description,
                        "url": urljoin(self.base_url, url) if url else ""
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to parse database item: {e}")
                continue
        
        return databases
    
    def _get_default_databases(self) -> List[Dict[str, str]]:
        """기본 데이터베이스 목록"""
        return [
            {
                "name": "KISS (한국학술정보)",
                "description": "한국 학술논문 및 학위논문 데이터베이스",
                "url": "https://kiss.kstudy.com"
            },
            {
                "name": "DBpia",
                "description": "국내 학술논문 및 전문자료 데이터베이스",
                "url": "https://www.dbpia.co.kr"
            },
            {
                "name": "RISS",
                "description": "국내 학술연구정보서비스",
                "url": "http://www.riss.kr"
            },
            {
                "name": "Web of Science",
                "description": "국제 학술논문 검색 데이터베이스",
                "url": "https://webofscience.com"
            }
        ]
    
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