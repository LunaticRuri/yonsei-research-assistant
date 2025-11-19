"""
Test script for _get_holdings_detailed_info method
상세 정보 추출 테스트 (제목, 저자, 자료유형, 발행사항, ISBN)
"""

import asyncio
import logging
from library_holdings_scraper import (
    LibraryHoldingsScraper,
    LibraryHoldingsSearchParams,
    SearchField,
    MaterialType
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_detail_extraction():
    """
    상세 정보 추출 테스트
    """
    
    print("=" * 80)
    print("Testing _get_holdings_detailed_info")
    print("=" * 80)
    
    scraper = LibraryHoldingsScraper()
    
    # 테스트 1: 인공지능 관련 도서 검색
    print("\n[Test 1] Search and extract details for AI books")
    print("-" * 80)
    
    params = LibraryHoldingsSearchParams(
        query="인공지능",
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params, max_results=3)
        
        print(f"\n✓ Retrieved {len(results)} results\n")
        
        for idx, result in enumerate(results, 1):
            print(f"Result #{idx}:")
            print(f"  제목: {result.get('title', 'N/A')}")
            print(f"  저자: {result.get('author', 'N/A')}")
            print(f"  자료유형: {result.get('material_type', 'N/A')}")
            print(f"  발행사항: {result.get('publication_info', 'N/A')}")
            print(f" 발행년도: {result.get('publication_year', 'N/A')}")
            print(f"  ISBN: {result.get('isbn', 'N/A')}")
            print(f"  Access ID: {result.get('access_id', 'N/A')}")
            print(f"  상세 URL: {result.get('detail_url', 'N/A')}")
            
            # 책 소개 출력 (있는 경우)
            description = result.get('book_description', '')
            if description:
                # 긴 경우 처음 200자만 표시
                if len(description) > 200:
                    print(f"  책 소개: {description[:200]}...")
                else:
                    print(f"  책 소개: {description}")
            else:
                print(f"  책 소개: (없음)")
            print()
    
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 대기
    await asyncio.sleep(2)
    
    # 테스트 2: 특정 저자로 검색
    print("\n[Test 2] Search by author")
    print("-" * 80)
    
    params2 = LibraryHoldingsSearchParams(
        query="이중원",
        search_field=SearchField.AUTHOR,
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params2, max_results=2)
        
        print(f"\n✓ Retrieved {len(results)} results\n")
        
        for idx, result in enumerate(results, 1):
            print(f"Result #{idx}:")
            print(f"  제목: {result.get('title', 'N/A')}")
            print(f"  저자: {result.get('author', 'N/A')}")
            print(f"  자료유형: {result.get('material_type', 'N/A')}")
            print(f"  발행사항: {result.get('publication_info', 'N/A')}")
            print(f" 발행년도: {result.get('publication_year', 'N/A')}")
            print(f"  ISBN: {result.get('isbn', 'N/A')}")
            
            description = result.get('book_description', '')
            if description:
                if len(description) > 150:
                    print(f"  책 소개: {description[:150]}...")
                else:
                    print(f"  책 소개: {description}")
            print()
    
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 대기
    await asyncio.sleep(2)
    
    # 테스트 3: 단행본만 검색
    print("\n[Test 3] Search only books (단행본)")
    print("-" * 80)
    
    params3 = LibraryHoldingsSearchParams(
        query="머신러닝",
        material_types=[MaterialType.BOOK],
        results_per_page=10
    )
    
    try:
        results = await scraper.execute_holdings_search(params3, max_results=2)
        
        print(f"\n✓ Retrieved {len(results)} results\n")
        
        for idx, result in enumerate(results, 1):
            print(f"Result #{idx}:")
            print(f"  제목: {result.get('title', 'N/A')}")
            print(f"  저자: {result.get('author', 'N/A')}")
            print(f"  자료유형: {result.get('material_type', 'N/A')} (should be '단행본')")
            print(f"  발행사항: {result.get('publication_info', 'N/A')}")
            print(f" 발행년도: {result.get('publication_year', 'N/A')}")
            print(f"  ISBN: {result.get('isbn', 'N/A')}")
            
            description = result.get('book_description', '')
            if description:
                if len(description) > 150:
                    print(f"  책 소개: {description[:150]}...")
                else:
                    print(f"  책 소개: {description}")
            print()
    
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)
    print("All tests completed!")
    print("=" * 80)


async def test_direct_access_id():
    """
    특정 access_id로 직접 상세 정보 가져오기 테스트
    """
    
    print("\n" + "=" * 80)
    print("Testing direct access with known access_id")
    print("=" * 80)
    
    scraper = LibraryHoldingsScraper()
    
    # 예시 access_id (실제 존재하는 ID로 테스트)
    # 먼저 검색으로 하나 가져오기
    params = LibraryHoldingsSearchParams(
        query="윤리학",
        results_per_page=10
    )
    
    try:
        # 검색으로 access_id 가져오기
        print("\n[Step 1] Getting access_id from search...")
        search_url = scraper._build_holdings_search_url(params, page=1)
        response = scraper.session.get(search_url, timeout=30)
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        first_item = soup.select_one('ul.resultList li.items')
        if first_item:
            item_id = first_item.get('id', '')
            if item_id.startswith('item_'):
                access_id = item_id.replace('item_', '')
                print(f"Found access_id: {access_id}")
                
                # 상세 정보 가져오기
                print(f"\n[Step 2] Fetching detailed info for {access_id}...")
                await asyncio.sleep(1)  # 윤리적 지연
                
                result = await scraper._get_holdings_detailed_info(access_id)
                
                print(f"\n✓ Successfully retrieved detailed info:\n")
                print(f"  제목: {result.get('title', 'N/A')}")
                print(f"  저자: {result.get('author', 'N/A')}")
                print(f"  자료유형: {result.get('material_type', 'N/A')}")
                print(f"  발행사항: {result.get('publication_info', 'N/A')}")
                print(f" 발행년도: {result.get('publication_year', 'N/A')}")
                print(f"  ISBN: {result.get('isbn', 'N/A')}")
                print(f"  Access ID: {result.get('access_id', 'N/A')}")
                print(f"  상세 URL: {result.get('detail_url', 'N/A')}")
                
                # 책 소개 출력
                description = result.get('book_description', '')
                if description:
                    if len(description) > 300:
                        print(f"  책 소개: {description[:300]}...")
                    else:
                        print(f"  책 소개: {description}")
                else:
                    print(f"  책 소개: (없음)")
            else:
                print("✗ Could not extract access_id")
        else:
            print("✗ No results found")
    
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 80)


if __name__ == "__main__":
    # 메인 테스트 실행
    asyncio.run(test_detail_extraction())
    
    # 직접 access_id 테스트
    asyncio.run(test_direct_access_id())
