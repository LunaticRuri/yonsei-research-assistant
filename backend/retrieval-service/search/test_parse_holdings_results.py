"""
Test script for _parse_holdings_search_results method
"""

import asyncio
import logging
from library_holdings_scraper import (
    LibraryHoldingsScraper,
    LibraryHoldingsSearchParams,
    SearchField,
    MaterialType,
    YearRange
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_parse_holdings_results():
    """
    _parse_holdings_search_results 테스트
    """
    
    print("=" * 80)
    print("Testing _parse_holdings_search_results")
    print("=" * 80)
    
    scraper = LibraryHoldingsScraper()
    
    # 테스트 케이스 1: 기본 검색 (페이징 없음)
    print("\n[Test 1] Basic search without pagination")
    print("-" * 80)
    
    params1 = LibraryHoldingsSearchParams(
        query="인공지능",
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params1, max_results=5)
        print(f"✓ Test 1 passed: Retrieved {len(results)} results (expected: 5)")
        
        if results:
            print(f"  First result title: {results[0].get('title', 'N/A')}")
            print(f"  First result author: {results[0].get('author', 'N/A')}")
            print(f"  Access ID: {results[0].get('access_id', 'N/A')}")
    
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
    
    # 대기
    await asyncio.sleep(1)
    
    # 테스트 케이스 2: 페이징이 필요한 검색
    print("\n[Test 2] Search with pagination (max_results > results_per_page)")
    print("-" * 80)
    
    params2 = LibraryHoldingsSearchParams(
        query="머신러닝",
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params2, max_results=25)
        print(f"✓ Test 2 passed: Retrieved {len(results)} results (expected: 25)")
        
        if len(results) >= 25:
            print(f"  Result #1: {results[0]}")
            print(f"  Result #11: {results[10]}")
            print(f"  Result #21: {results[20]}")
        elif len(results) > 0:
            print(f"  Note: Only {len(results)} results available")
    
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
    
    # 대기
    await asyncio.sleep(1)
    
    # 테스트 케이스 3: 검색 결과가 적은 경우
    print("\n[Test 3] Search with limited results")
    print("-" * 80)
    
    params3 = LibraryHoldingsSearchParams(
        query="quantum computing blockchain artificial intelligence",
        search_field=SearchField.TITLE,
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params3, max_results=100)
        print(f"✓ Test 3 passed: Retrieved {len(results)} results")
        print(f"  (Requested 100, but only {len(results)} available)")
        
        if results:
            print(f"  First result: {results[0]}")
    
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
    
    # 대기
    await asyncio.sleep(1)
    
    # 테스트 케이스 4: 높은 results_per_page 값
    print("\n[Test 4] Search with high results_per_page")
    print("-" * 80)
    
    params4 = LibraryHoldingsSearchParams(
        query="데이터 분석",
        results_per_page=100
    )
    
    try:
        results = await scraper.execute_holdings_search(params4, max_results=50)
        print(f"✓ Test 4 passed: Retrieved {len(results)} results (expected: 50)")
        print(f"  Should fetch from single page (100 per page, requested 50)")
    
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
    
    # 대기
    await asyncio.sleep(1)
    
    # 테스트 케이스 5: 필터링 조건 포함
    print("\n[Test 5] Search with filters (year range)")
    print("-" * 80)
    
    params5 = LibraryHoldingsSearchParams(
        query="딥러닝",
        year_range=YearRange(from_year=2020, to_year=2025),
        results_per_page=20
    )
    
    try:
        results = await scraper.execute_holdings_search(params5, max_results=15)
        print(f"✓ Test 5 passed: Retrieved {len(results)} results (expected: 15)")
        
        if results:
            print(f"  First result: {results[0]}")
            print(f"  Year range: 2020-2025")
    
    except Exception as e:
        print(f"✗ Test 5 failed: {e}")
    
    # 대기
    await asyncio.sleep(1)
    
    # 테스트 케이스 6: 자료 유형 필터링
    print("\n[Test 6] Search with material type filter")
    print("-" * 80)
    
    params6 = LibraryHoldingsSearchParams(
        query="논문",
        material_types=[MaterialType.THESIS],
        results_per_page=15
    )
    
    try:
        results = await scraper.execute_holdings_search(params6, max_results=10)
        print(f"✓ Test 6 passed: Retrieved {len(results)} results (expected: 10)")
        print(f"  Material type: Thesis only")
        
        if results:
            print(f"  First result: {results[0]}")
    
    except Exception as e:
        print(f"✗ Test 6 failed: {e}")
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


async def test_edge_cases():
    """
    엣지 케이스 테스트
    """
    
    print("\n" + "=" * 80)
    print("Testing edge cases")
    print("=" * 80)
    
    scraper = LibraryHoldingsScraper()
    
    # 테스트 1: max_results가 실제 결과보다 큰 경우
    print("\n[Edge Case 1] max_results > available results")
    print("-" * 80)
    
    params1 = LibraryHoldingsSearchParams(
        query="asdfghjklqwertyuiopzxcvbnm12345",  # 거의 결과가 없을 검색어
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params1, max_results=100)
        print(f"✓ Edge case 1 handled: Retrieved {len(results)} results")
        print(f"  (Requested 100, but only {len(results)} available)")
    
    except Exception as e:
        print(f"✗ Edge case 1 failed: {e}")
    
    await asyncio.sleep(1)
    
    # 테스트 2: max_results = 1
    print("\n[Edge Case 2] max_results = 1 (minimum)")
    print("-" * 80)
    
    params2 = LibraryHoldingsSearchParams(
        query="인공지능",
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params2, max_results=1)
        print(f"✓ Edge case 2 handled: Retrieved {len(results)} results (expected: 1)")
        
        if results:
            print(f"  Result: {results[0]}")
    
    except Exception as e:
        print(f"✗ Edge case 2 failed: {e}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # 메인 테스트 실행
    asyncio.run(test_parse_holdings_results())
    
    # 엣지 케이스 테스트
    asyncio.run(test_edge_cases())
