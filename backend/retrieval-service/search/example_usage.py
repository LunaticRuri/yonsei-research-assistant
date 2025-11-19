"""
LibraryScraper의 Pydantic 기반 인터페이스 사용 예시

이 파일은 새로운 LibrarySearchParams 모델을 사용하는 방법을 보여줍니다.
"""

import asyncio
import logging
from library_holdings_scraper import (
    LibraryHoldingsScraper,
    LibraryHoldingsSearchParams,
    SearchField,
    MaterialType,
    QueryOperator,
    AdditionalQuery,
    YearRange
)
from electronic_resource_scraper import ElectronicResourceScraper
from shared.models import ElectronicResourceInfo

logger = logging.getLogger(__name__)

async def example_1_simple_search():
    """예시 1: 간단한 검색"""
    print("\n=== 예시 1: 간단한 검색 ===")
    
    async with LibraryHoldingsScraper() as scraper:
        # Pydantic 모델을 사용한 검색 파라미터 구성
        params = LibraryHoldingsSearchParams(
            query="인공지능",
            results_per_page=20
        )
        
        # 검색 실행
        results = await scraper.execute_holdings_search(params, max_results=5)
        
        print(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            # print(f"{i}. {result.title or 'N/A'}")
            print(f"===== {i} =====")
            print(result.model_dump_json(indent=2))


async def example_2_advanced_search():
    """예시 2: 고급 검색 - OR/NOT 연산자 사용"""
    print("\n=== 예시 2: 고급 검색 (휴대폰 OR 스마트폰 NOT 아이폰) ===")
    
    async with LibraryHoldingsScraper() as scraper:
        params = LibraryHoldingsSearchParams(
            query="휴대폰",
            additional_queries=[
                AdditionalQuery(
                    query="스마트폰",
                    operator=QueryOperator.OR
                ),
                AdditionalQuery(
                    query="아이폰",
                    operator=QueryOperator.NOT
                )
            ],
            year_range=YearRange(from_year=2020, to_year=2025),
            results_per_page=50
        )
        
        results = await scraper.execute_holdings_search(params, max_results=5)
        
        print(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title or 'N/A'} ({result.publication_year or 'N/A'})")


async def example_3_field_specific_search():
    """예시 3: 필드별 검색"""
    print("\n=== 예시 3: 필드별 검색 (서명='머신러닝' AND 저자='김철수') ===")
    
    async with LibraryHoldingsScraper() as scraper:
        params = LibraryHoldingsSearchParams(
            query="머신러닝",
            search_field=SearchField.TITLE,  # 서명으로 검색
            additional_queries=[
                AdditionalQuery(
                    search_field=SearchField.AUTHOR,  # 저자 필드
                    query="김철수",
                    operator=QueryOperator.AND
                ),
                AdditionalQuery(
                    search_field=SearchField.SUBJECT,  # 주제어 필드
                    query="딥러닝",
                    operator=QueryOperator.AND
                )
            ],
            results_per_page=100
        )
        
        results = await scraper.execute_holdings_search(params, max_results=5)
        
        print(f"검색 결과: {len(results)}건")


async def example_4_material_type_filter():
    """예시 4: 자료 유형 필터링"""
    print("\n=== 예시 4: 자료 유형 필터 (연속간행물 + 학위논문만) ===")
    
    async with LibraryHoldingsScraper() as scraper:
        params = LibraryHoldingsSearchParams(
            query="기후변화",
            material_types=[
                MaterialType.SERIAL,   # 연속간행물
                MaterialType.THESIS    # 학위논문
            ],
            year_range=YearRange(from_year=2020),
            results_per_page=30
        )
        
        results = await scraper.execute_holdings_search(params, max_results=5)
        
        print(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title or 'N/A'} - {result.material_type or 'N/A'}")


async def example_5_complex_query():
    """예시 5: 복잡한 쿼리 조합"""
    print("\n=== 예시 5: 복잡한 쿼리 ===")
    
    async with LibraryHoldingsScraper() as scraper:
        params = LibraryHoldingsSearchParams(
            query="블록체인",
            search_field=SearchField.SUBJECT,
            additional_queries=[
                AdditionalQuery(
                    search_field=SearchField.TITLE,
                    query="암호화폐",
                    operator=QueryOperator.OR
                ),
                AdditionalQuery(
                    search_field=SearchField.AUTHOR,
                    query="홍길동",
                    operator=QueryOperator.AND
                )
            ],
            material_types=[MaterialType.BOOK, MaterialType.THESIS],
            year_range=YearRange(from_year=2018, to_year=2024),
            results_per_page=50
        )
        
        results = await scraper.execute_holdings_search(params, max_results=3)
        
        print(f"검색 결과: {len(results)}건")

async def example_6_validation():
    """예시 6: 자동 검증"""
    print("\n=== 예시 6: Pydantic 자동 검증 ===")
    
    try:
        # 잘못된 연도 범위 - 자동으로 검증 오류 발생
        params = LibraryHoldingsSearchParams(
            query="테스트",
            year_range=YearRange(from_year=2025, to_year=2020)  # 오류!
        )
    except ValueError as e:
        print(f"✓ 검증 오류 감지: {e}")
    
    try:
        # 빈 검색어 - 자동으로 검증 오류 발생
        params = LibraryHoldingsSearchParams(query="")  # 오류!
    except ValueError as e:
        print(f"✓ 검증 오류 감지: {e}")
    
    try:
        # 잘못된 results_per_page 값
        params = LibraryHoldingsSearchParams(
            query="테스트",
            results_per_page=25  # Literal[5, 10, 15, 20, 30, 50, 100]에 없음
        )
    except ValueError as e:
        print(f"✓ 검증 오류 감지: {e}")
    
    print("\n모든 검증 테스트 통과!")


async def example_7_electronic_resource_search():
    """예시 7: 전자자료(논문, E-Book 등) 검색"""
    print("\n=== 예시 7: 전자자료 검색 (논문/전자책) ===")
    async with ElectronicResourceScraper() as scraper:
        params = LibraryHoldingsSearchParams(
            query="인공지능",
            results_per_page=10
        )
        results = await scraper.execute_electronic_search(params, max_results=3)
        print(f"전자자료 검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title or 'N/A'} | {result.resource_type or 'N/A'} | {result.link_url or 'N/A'}")

async def main():
    """모든 예시 실행"""
    print("=" * 60)
    print("LibrarySearchParams 사용 예시")
    print("=" * 60)
    try:
        await example_6_validation()
        print("\n" + "=" * 60)
        print("주의: 나머지 예시는 실제 도서관 웹사이트에 요청을 보냅니다.")
        print("=" * 60)
        await example_1_simple_search()
        # await example_2_advanced_search()
        # await example_3_field_specific_search()
        # await example_4_material_type_filter()
        # await example_5_complex_query()
        # await example_7_electronic_resource_search()
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())
