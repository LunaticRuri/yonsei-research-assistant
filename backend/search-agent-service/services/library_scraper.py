import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote
import asyncio
import aiohttp
from shared.models import DocumentResult


logger = logging.getLogger(__name__)

class LibraryScraper:
    """연세대학교 도서관 웹사이트 스크래핑"""
    
    def __init__(self):
        self.base_url = "https://library.yonsei.ac.kr"
        self.search_endpoints = {
            "holdings": "/search/tot",
            "electronic": "/eds/brief",
            "holdings_detail": "/search/detail", 
            "electronic_detail": "/eds/detail",
        }
        
        # 요청 간격 (윤리적 스크래핑)  
        self.request_delay = 1.0
        
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
        search_type: str = "holdings",
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """도서관 통합검색 실행"""
        # TODO: 검색 수행시 생각해봐야할 것들. 처음엔 학술정보원 사이트 검색을 사용하되, 어느 정도 자료가 줄어들면 임베딩 활용해서 검색 결과의 해석 및 필터링 기능 향상 가능함.
        
        # TODO: 기능 확장시 지우기
        if search_type != "holdings":
            raise NotImplementedError("현재는 'holdings' 검색만 지원합니다.")

        try:
            # 검색 URL 구성
            search_url = self._build_search_url(query, search_type)
            
            logger.info(f"Executing library search: {search_url}")
            
            # 검색 요청
            response = self.session.get(search_url, timeout=10)
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
    
    async def fetch_document(self, code: str) -> Optional[DocumentResult]:
        """특정 자료의 정보 확인"""
        
        document_type = "holdings" if code.startswith("CATTOT") else "electronic"
        if document_type == "holdings":
            detail_url = f"{self.base_url}{self.search_endpoints['holdings_detail']}/{code}"
        else:
            detail_url = f"{self.base_url}{self.search_endpoints['electronic_detail']}/{code}"

        try:
            response = self.session.get(detail_url, timeout=10)
            response.raise_for_status()

            result = await self._parse_detail(response.text, document_type)
            return result
            
        except Exception as e:
            logger.error(f"Holdings check failed for '{code}': {e}")
            return None

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
    
    def _build_search_url(self, query: str, search_type: str) -> str:
        """검색 URL 구성"""
        
        endpoint = self.search_endpoints.get(search_type, self.search_endpoints["holdings"])
        encoded_query = quote(query)
        

        # 기본 검색 매개변수
        params = {
            'q': encoded_query,
            'page': 1,
            'size': 20,
            'sort': 'relevance'
        }
        
        # URL 매개변수 문자열 구성
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        
        return f"{self.base_url}{endpoint}?{param_string}"
    
    def _parse_search_results(self, html_content: str, search_type: str) -> List[Dict[str, Any]]:
        """검색 결과 파싱"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        # TODO: 결과 파싱
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
    
    async def _parse_detail(self, html_content: str, search_type: str) -> List[Dict[str, Any]]:
        """검색 결과 파싱 - 검색 타입에 따라 적절한 파서 호출"""
        
        if search_type == "holdings":
            return await self._parse_holdings_detail(html_content)
        elif search_type == "electronic":
            return await self._parse_electronic_detail(html_content)
        else:
            raise ValueError(f"Unknown search type: {search_type}")

    async def _parse_holdings_detail(self, html_content: str) -> DocumentResult:
        """소장자료 검색 결과 파싱"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        if "현재페이지가 존재하지 않거나, 현재 이용할 수 없는 페이지 입니다." in html_content:
            return False

        ...

    async def _parse_electronic_detail(self, html_content: str) -> DocumentResult:
        """전자자료 검색 결과 파싱"""
        
        soup = BeautifulSoup(html_content, 'html.parser')

        if "현재페이지가 존재하지 않거나, 현재 이용할 수 없는 페이지 입니다." in html_content:
            return False
        
        ...
    
    def _generate_mock_holdings(self) -> Dict[str, Any]:
        """Mock 소장 정보 생성"""
        # TODO: 나중에 실제 데이터 형식에 맞게 수정해야 함.
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
    
    def __del__(self):
        """소멸자: 세션 정리"""
        if hasattr(self, 'session'):
            self.session.close()