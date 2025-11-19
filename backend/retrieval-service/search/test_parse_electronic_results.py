"""
Test script for _parse_electronic_search_results function
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
service_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(service_root)

from electronic_resource_scraper import (
    ElectronicResourceScraper,
    ElectronicSearchParams,
    SearchField,
    QueryOperator,
    AdditionalQuery,
    YearRange
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_parse_electronic_search_results():
    """_parse_electronic_search_results 함수 테스트"""
    
    logger.info("=" * 80)
    logger.info("Testing _parse_electronic_search_results function")
    logger.info("=" * 80)
    
    # 스크래퍼 인스턴스 생성
    scraper = ElectronicResourceScraper()
    
    # 테스트 케이스 1: 간단한 검색 (max_result=10)
    logger.info("\n[Test 1] Simple search with max_result=10")
    params1 = ElectronicSearchParams(
        query="machine learning",
        search_field=SearchField.KEYWORD,
        results_per_page=10,
        academic_journals_only=True,
        year_range=YearRange(from_year=2020, to_year=2025)
    )
    
    try:
        # URL 생성 및 첫 페이지 HTML 가져오기
        search_url = scraper._build_electronic_search_url(params1, page=1)
        logger.info(f"Search URL: {search_url}")
        
        html_content = await scraper._fetch(search_url)
        logger.info(f"Fetched HTML content length: {len(html_content)} chars")
        
        # _parse_electronic_search_results 호출
        results = await scraper._parse_electronic_search_results(
            html_content=html_content,
            max_result=10,
            params=params1
        )
        
        logger.info(f"Results count: {len(results)}")
        logger.info(f"First 3 access IDs:")
        for i, access_id in enumerate(results[:3], 1):
            logger.info(f"  {i}. {access_id}")
        
    except Exception as e:
        logger.error(f"Test 1 failed: {e}", exc_info=True)
    
    await asyncio.sleep(2)  # 요청 간 지연
    
    # 테스트 케이스 2: 복수 페이지 검색 (max_result=50)
    logger.info("\n[Test 2] Multi-page search with max_result=50")
    params2 = ElectronicSearchParams(
        query="artificial intelligence",
        search_field=SearchField.TITLE,
        results_per_page=20,
        academic_journals_only=True,
        year_range=YearRange(from_year=2022, to_year=2025)
    )
    
    try:
        search_url = scraper._build_electronic_search_url(params2, page=1)
        logger.info(f"Search URL: {search_url}")
        
        html_content = await scraper._fetch(search_url)
        logger.info(f"Fetched HTML content length: {len(html_content)} chars")
        
        # _parse_electronic_search_results 호출 (페이징 포함)
        results = await scraper._parse_electronic_search_results(
            html_content=html_content,
            max_result=50,
            params=params2
        )
        
        logger.info(f"Results count: {len(results)}")
        logger.info(f"Sample access IDs:")
        for i in [0, 10, 20, 30, 40]:
            if i < len(results):
                logger.info(f"  [{i}] {results[i]}")
        
    except Exception as e:
        logger.error(f"Test 2 failed: {e}", exc_info=True)
    
    await asyncio.sleep(2)
    
    # 테스트 케이스 3: 추가 검색 조건 포함
    logger.info("\n[Test 3] Search with additional queries")
    params3 = ElectronicSearchParams(
        query="deep learning",
        search_field=SearchField.KEYWORD,
        additional_queries=[
            AdditionalQuery(
                search_field=SearchField.SUBJECT,
                query="neural networks",
                operator=QueryOperator.AND
            ),
            AdditionalQuery(
                search_field=SearchField.KEYWORD,
                query="computer vision",
                operator=QueryOperator.OR
            )
        ],
        results_per_page=20,
        academic_journals_only=True,
        year_range=YearRange(from_year=2021, to_year=2025)
    )
    
    try:
        search_url = scraper._build_electronic_search_url(params3, page=1)
        logger.info(f"Search URL: {search_url}")
        
        html_content = await scraper._fetch(search_url)
        logger.info(f"Fetched HTML content length: {len(html_content)} chars")
        
        results = await scraper._parse_electronic_search_results(
            html_content=html_content,
            max_result=30,
            params=params3
        )
        
        logger.info(f"Results count: {len(results)}")
        logger.info(f"First 5 access IDs:")
        for i, access_id in enumerate(results[:5], 1):
            logger.info(f"  {i}. {access_id}")
        
    except Exception as e:
        logger.error(f"Test 3 failed: {e}", exc_info=True)
    
    await asyncio.sleep(2)
    
    # 테스트 케이스 4: max_result가 실제 결과보다 큰 경우
    logger.info("\n[Test 4] max_result larger than available results")
    params4 = ElectronicSearchParams(
        query="quantum computing blockchain AI security",  # 아주 구체적인 검색
        search_field=SearchField.TITLE,
        results_per_page=20,
        academic_journals_only=True,
        year_range=YearRange(from_year=2024, to_year=2025)
    )
    
    try:
        search_url = scraper._build_electronic_search_url(params4, page=1)
        logger.info(f"Search URL: {search_url}")
        
        html_content = await scraper._fetch(search_url)
        logger.info(f"Fetched HTML content length: {len(html_content)} chars")
        
        results = await scraper._parse_electronic_search_results(
            html_content=html_content,
            max_result=1000,  # 실제 결과보다 큰 값
            params=params4
        )
        
        logger.info(f"Results count: {len(results)}")
        logger.info("This should be limited by available results, not max_result")
        
    except Exception as e:
        logger.error(f"Test 4 failed: {e}", exc_info=True)
    
    # 세션 정리
    await scraper.close()
    
    logger.info("\n" + "=" * 80)
    logger.info("All tests completed")
    logger.info("=" * 80)


async def test_parse_without_pagination():
    """페이징 없이 단일 HTML 파싱만 테스트"""
    
    logger.info("\n" + "=" * 80)
    logger.info("Testing _parse_electronic_search_results (single page only)")
    logger.info("=" * 80)
    
    scraper = ElectronicResourceScraper()
    
    params = ElectronicSearchParams(
        query="data science",
        search_field=SearchField.KEYWORD,
        results_per_page=20,
        academic_journals_only=True
    )
    
    try:
        search_url = scraper._build_electronic_search_url(params, page=1)
        logger.info(f"Search URL: {search_url}")
        
        html_content = await scraper._fetch(search_url)
        logger.info(f"Fetched HTML content length: {len(html_content)} chars")
        
        # params=None으로 설정하여 페이징 비활성화
        results = await scraper._parse_electronic_search_results(
            html_content=html_content,
            max_result=100,
            params=None  # 페이징 없음
        )
        
        logger.info(f"Results count (should be ≤ results_per_page): {len(results)}")
        logger.info(f"All access IDs:")
        for i, access_id in enumerate(results, 1):
            logger.info(f"  {i}. {access_id}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    
    await scraper.close()


async def main():
    """메인 함수"""
    
    print("\n" + "=" * 80)
    print("Electronic Resource Search Results Parser Test")
    print("=" * 80 + "\n")
    
    # 테스트 선택 메뉴
    print("Select test to run:")
    print("1. Full test suite (all test cases)")
    print("2. Parse without pagination (single page only)")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        await test_parse_electronic_search_results()
    elif choice == "2":
        await test_parse_without_pagination()
    elif choice == "3":
        await test_parse_electronic_search_results()
        print("\n" + "="*80 + "\n")
        await test_parse_without_pagination()
    else:
        print("Invalid choice. Running full test suite...")
        await test_parse_electronic_search_results()


if __name__ == "__main__":
    asyncio.run(main())
