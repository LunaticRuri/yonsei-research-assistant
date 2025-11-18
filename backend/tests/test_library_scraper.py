import pytest
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# 프로젝트 루트를 Python 경로에 추가
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# retrieval-service의 search 모듈 import
retrieval_service_path = backend_path / "retrieval-service"
sys.path.insert(0, str(retrieval_service_path))

from search.library_scraper import LibraryScraper


@pytest.fixture
def scraper():
    """LibraryScraper 인스턴스 생성"""
    return LibraryScraper()


class TestBuildSearchURL:
    """_build_search_url 메서드 테스트"""
    
    def test_basic_search(self, scraper):
        """기본 검색 URL 생성 테스트"""
        url = scraper._build_search_url(
            query="인공지능",
            search_type="integrated"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 기본 파라미터 검증
        assert parsed.path == "/search/tot/result"
        assert params['st'][0] == 'KWRD'
        assert params['commandType'][0] == 'advanced'
        assert params['q'][0] == '인공지능'
        assert params['si'][0] == 'TOTAL'
        assert params['lmt0'][0] == 'TOTAL'
        assert params['cpp'][0] == '10'
    
    def test_search_with_year_range(self, scraper):
        """발행년도 범위 설정 테스트"""
        url = scraper._build_search_url(
            query="머신러닝",
            search_type="integrated",
            year_from="2020",
            year_to="2025"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['rf'][0] == '2020'
        assert params['rt'][0] == '2025'
        assert params['range'][0] == '000000000021'
    
    def test_search_with_or_operator(self, scraper):
        """OR 연산자 테스트: 휴대폰 OR 스마트폰"""
        url = scraper._build_search_url(
            query="휴대폰",
            search_type="integrated",
            additional_queries=[
                {"si": "TOTAL", "q": "스마트폰", "operator": "or"}
            ]
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 첫 번째 검색어
        assert params['q'][0] == '휴대폰'
        
        # OR 연산자와 두 번째 검색어
        assert params['b0'][0] == 'or'
        assert params['q'][1] == '스마트폰'
    
    def test_search_with_not_operator(self, scraper):
        """NOT 연산자 테스트: 노동 NOT 북한"""
        url = scraper._build_search_url(
            query="노동",
            search_type="integrated",
            additional_queries=[
                {"si": "TOTAL", "q": "북한", "operator": "not"}
            ]
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['q'][0] == '노동'
        assert params['b0'][0] == 'not'
        assert params['q'][1] == '북한'
    
    def test_complex_search_or_and_not(self, scraper):
        """복잡한 검색: 휴대폰 OR 스마트폰 NOT 아이폰"""
        url = scraper._build_search_url(
            query="휴대폰",
            search_type="integrated",
            additional_queries=[
                {"si": "TOTAL", "q": "스마트폰", "operator": "or"},
                {"si": "TOTAL", "q": "아이폰", "operator": "not"}
            ]
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 검색어 순서 확인
        assert params['q'][0] == '휴대폰'
        assert params['q'][1] == '스마트폰'
        assert params['q'][2] == '아이폰'
        
        # 연산자 확인
        assert params['b0'][0] == 'or'
        assert params['b1'][0] == 'not'
        
        # weight 파라미터 확인
        assert 'weight0' in params
        assert 'weight1' in params
        assert 'weight2' in params
    
    def test_multiple_not_operators(self, scraper):
        """여러 NOT 연산자 테스트: 노동 NOT 북한 NOT 조선"""
        url = scraper._build_search_url(
            query="노동",
            search_type="integrated",
            additional_queries=[
                {"si": "TOTAL", "q": "북한", "operator": "not"},
                {"si": "TOTAL", "q": "조선", "operator": "not"}
            ],
            year_from="2020",
            year_to="2025"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 검색어 확인
        assert params['q'][0] == '노동'
        assert params['q'][1] == '북한'
        assert params['q'][2] == '조선'
        
        # 연산자 확인
        assert params['b0'][0] == 'not'
        assert params['b1'][0] == 'not'
        
        # 발행년도 확인
        assert params['rf'][0] == '2020'
        assert params['rt'][0] == '2025'
    
    def test_results_per_page(self, scraper):
        """쪽당 출력 건수 설정 테스트"""
        url = scraper._build_search_url(
            query="테스트",
            search_type="integrated",
            results_per_page=100
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['cpp'][0] == '100'
    
    def test_books_search_type(self, scraper):
        """단행본 검색 타입 테스트"""
        url = scraper._build_search_url(
            query="파이썬",
            search_type="books"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['lmt0'][0] == 'm'  # 단행본
    
    def test_articles_search_type(self, scraper):
        """기사 검색 타입 테스트"""
        url = scraper._build_search_url(
            query="코로나",
            search_type="articles"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['lmt0'][0] == 'zart'  # 기사
    
    def test_thesis_search_type(self, scraper):
        """학위논문 검색 타입 테스트"""
        url = scraper._build_search_url(
            query="딥러닝",
            search_type="thesis"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['lmt0'][0] == 't'  # 학위논문
    
    def test_url_encoding(self, scraper):
        """한글 및 특수문자 URL 인코딩 테스트"""
        url = scraper._build_search_url(
            query="인공지능 & 머신러닝",
            search_type="integrated"
        )
        
        # URL이 정상적으로 생성되는지 확인
        assert url.startswith("https://library.yonsei.ac.kr/search/tot/result?")
        assert "q=" in url
    
    def test_full_example_url(self, scraper):
        """
        실제 예시 URL 재현 테스트:
        휴대폰 OR 스마트폰 NOT 아이폰 (2020-2025, 100건)
        """
        url = scraper._build_search_url(
            query="휴대폰",
            search_type="integrated",
            additional_queries=[
                {"si": "TOTAL", "q": "스마트폰", "operator": "or"},
                {"si": "TOTAL", "q": "아이폰", "operator": "not"}
            ],
            year_from="2020",
            year_to="2025",
            results_per_page=100
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 모든 주요 파라미터 검증
        assert params['st'][0] == 'KWRD'
        assert params['commandType'][0] == 'advanced'
        assert params['q'][0] == '휴대폰'
        assert params['q'][1] == '스마트폰'
        assert params['q'][2] == '아이폰'
        assert params['b0'][0] == 'or'
        assert params['b1'][0] == 'not'
        assert params['rf'][0] == '2020'
        assert params['rt'][0] == '2025'
        assert params['cpp'][0] == '100'
        assert params['lmt0'][0] == 'TOTAL'
        assert params['lmt1'][0] == 'TOTAL'
        assert params['msc'][0] == '10000'
    
    def test_search_with_specific_fields(self, scraper):
        """
        필드별 검색 테스트:
        서명='휴대폰' AND 저자='김철수' AND 주제어='아이폰'
        """
        url = scraper._build_search_url(
            query="휴대폰",
            search_type="integrated",
            search_field="1",  # 서명
            additional_queries=[
                {"si": "2", "q": "김철수", "operator": "and"},  # 저자
                {"si": "4", "q": "아이폰", "operator": "and"}   # 주제어
            ],
            year_from="2020",
            year_to="2025",
            results_per_page=100
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 검색어와 검색 항목 검증
        assert params['si'][0] == '1'  # 서명
        assert params['q'][0] == '휴대폰'
        
        assert params['si'][1] == '2'  # 저자
        assert params['q'][1] == '김철수'
        
        assert params['si'][2] == '4'  # 주제어
        assert params['q'][2] == '아이폰'
        
        # 연산자 검증
        assert params['b0'][0] == 'and'
        assert params['b1'][0] == 'and'
        
        # 기타 파라미터 검증
        assert params['rf'][0] == '2020'
        assert params['rt'][0] == '2025'
        assert params['cpp'][0] == '100'
    
    def test_search_field_title(self, scraper):
        """서명(책제목) 검색 필드 테스트"""
        url = scraper._build_search_url(
            query="파이썬",
            search_type="integrated",
            search_field="1"  # 서명
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['si'][0] == '1'
        assert params['q'][0] == '파이썬'
    
    def test_search_field_author(self, scraper):
        """저자 검색 필드 테스트"""
        url = scraper._build_search_url(
            query="김철수",
            search_type="integrated",
            search_field="2"  # 저자
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['si'][0] == '2'
        assert params['q'][0] == '김철수'
    
    def test_search_field_publisher(self, scraper):
        """출판사 검색 필드 테스트"""
        url = scraper._build_search_url(
            query="한빛미디어",
            search_type="integrated",
            search_field="3"  # 출판사
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['si'][0] == '3'
        assert params['q'][0] == '한빛미디어'
    
    def test_search_field_subject(self, scraper):
        """주제어 검색 필드 테스트"""
        url = scraper._build_search_url(
            query="인공지능",
            search_type="integrated",
            search_field="4"  # 주제어
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert params['si'][0] == '4'
        assert params['q'][0] == '인공지능'
    
    def test_multiple_material_types(self, scraper):
        """
        여러 자료유형 선택 테스트:
        연속간행물(s)과 학위논문(t) 선택
        """
        url = scraper._build_search_url(
            query="휴대폰",
            search_type="integrated",
            material_types=["s", "t"]
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # lmt0 파라미터에 's'와 't'가 포함되어야 함
        assert 's' in params.get('lmt0', [])
        assert 't' in params.get('lmt0', [])
        
        # TOTAL이나 다른 유형은 포함되지 않아야 함
        assert 'TOTAL' not in params.get('lmt0', [])
        assert 'm' not in params.get('lmt0', [])
    
    def test_single_material_type(self, scraper):
        """단일 자료유형 선택 테스트: 학위논문만"""
        url = scraper._build_search_url(
            query="인공지능",
            search_type="integrated",
            material_types=["t"]
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        assert 't' in params.get('lmt0', [])
        assert len(params.get('lmt0', [])) == 1
    
    def test_all_material_types(self, scraper):
        """모든 자료유형 선택 테스트"""
        url = scraper._build_search_url(
            query="테스트",
            search_type="integrated",
            material_types=["m", "s", "b;p;v;x;u;c", "t", "o", "zart"]
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 모든 자료유형이 포함되어야 함
        lmt0_values = params.get('lmt0', [])
        assert 'm' in lmt0_values  # 단행본
        assert 's' in lmt0_values  # 연속간행물
        assert 't' in lmt0_values  # 학위논문
        assert 'zart' in lmt0_values  # 기사
    
    def test_material_types_with_search_type_books(self, scraper):
        """search_type='books'일 때 기본 자료유형"""
        url = scraper._build_search_url(
            query="파이썬",
            search_type="books"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # material_types가 지정되지 않으면 search_type에 따라 'm' 선택
        assert 'm' in params.get('lmt0', [])


class TestURLStructure:
    """URL 구조 및 필수 파라미터 테스트"""
    
    def test_required_parameters_present(self, scraper):
        """필수 파라미터 존재 확인"""
        url = scraper._build_search_url(
            query="테스트",
            search_type="integrated"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        required_params = [
            'st', 'commandType', 'si', 'q',
            'lmt0', 'lmtsn', 'lmtst',
            'inc', 'lmt1', 'lmt2',
            'cpp', 'msc'
        ]
        
        for param in required_params:
            assert param in params, f"필수 파라미터 '{param}'가 누락되었습니다"
    
    def test_base_url(self, scraper):
        """베이스 URL 확인"""
        url = scraper._build_search_url(
            query="테스트",
            search_type="integrated"
        )
        
        assert url.startswith("https://library.yonsei.ac.kr/search/tot/result?")
    
    def test_location_parameter(self, scraper):
        """소장처 파라미터 확인 (신촌+국제)"""
        url = scraper._build_search_url(
            query="테스트",
            search_type="integrated"
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # 신촌+국제 소장처 코드 확인
        assert 'lmt2' in params
        locations = params['lmt2'][0]
        assert 'YNLIB' in locations
        assert 'UML' in locations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
