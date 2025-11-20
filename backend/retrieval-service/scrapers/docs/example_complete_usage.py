"""
연세대학교 도서관 스크래퍼 사용 예시
LibraryHoldingsScraper와 ElectronicResourceScraper 모두 로그인 기능 포함

Setup:
1. .env 파일 생성 (이 파일과 같은 디렉토리)
2. 환경변수 설정:
   YONSEI_ID=your_id
   YONSEI_PW=your_password
3. 필수 패키지 설치:
   pip install python-dotenv playwright beautifulsoup4 aiohttp pydantic
   playwright install chromium
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
service_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(service_root)

from library_holdings_scraper import (
    LibraryHoldingsScraper,
    LibraryHoldingsSearchParams,
    SearchField,
    MaterialType,
    QueryOperator,
    AdditionalQuery,
    YearRange
)
from electronic_resource_scraper import (
    ElectronicResourceScraper,
    ElectronicSearchParams,
    SearchField as ElectronicSearchField,
    QueryOperator as ElectronicQueryOperator,
    AdditionalQuery as ElectronicAdditionalQuery,
    YearRange as ElectronicYearRange
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경변수에서 자격증명 가져오기
YONSEI_ID = os.getenv("YONSEI_ID")
YONSEI_PW = os.getenv("YONSEI_PW")


# ============================================================================
# LibraryHoldingsScraper 사용 예시 (소장자료 검색)
# ============================================================================

async def example_holdings_1_simple():
    """소장자료 예시 1: 기본 검색"""
    print("\n" + "=" * 80)
    print("소장자료 예시 1: 기본 검색 - '인공지능'")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    # async with를 사용하면 자동으로 로그인/로그아웃 처리됨
    async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = LibraryHoldingsSearchParams(
            query="인공지능",
            results_per_page=20
        )
        
        results = await scraper.execute_holdings_search(params, max_results=5)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.title}")
            print(f"    저자: {', '.join(result.author) if result.author else 'N/A'}")
            print(f"    출판년도: {result.publication_year or 'N/A'}")
            print(f"    자료유형: {result.material_type or 'N/A'}")
            print(f"    청구기호: {result.call_number or 'N/A'}")
    
    logger.info("로그아웃 완료")


async def example_holdings_2_advanced():
    """소장자료 예시 2: 고급 검색 (OR/AND 조합)"""
    print("\n" + "=" * 80)
    print("소장자료 예시 2: 고급 검색 - '머신러닝' OR '딥러닝' (2020년 이후)")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = LibraryHoldingsSearchParams(
            query="머신러닝",
            search_field=SearchField.KEYWORD,
            additional_queries=[
                AdditionalQuery(
                    query="딥러닝",
                    operator=QueryOperator.OR
                )
            ],
            year_range=YearRange(from_year=2020, to_year=2025),
            results_per_page=20
        )
        
        results = await scraper.execute_holdings_search(params, max_results=10)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.title}")
            print(f"    출판년도: {result.publication_year or 'N/A'}")
            print(f"    출판사: {result.publisher or 'N/A'}")


async def example_holdings_3_field_specific():
    """소장자료 예시 3: 필드별 검색"""
    print("\n" + "=" * 80)
    print("소장자료 예시 3: 필드별 검색 - 제목='데이터' AND 저자 포함")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = LibraryHoldingsSearchParams(
            query="데이터",
            search_field=SearchField.TITLE,
            additional_queries=[
                AdditionalQuery(
                    search_field=SearchField.AUTHOR,
                    query="김",
                    operator=QueryOperator.AND
                )
            ],
            results_per_page=20
        )
        
        results = await scraper.execute_holdings_search(params, max_results=5)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.title}")
            print(f"    저자: {', '.join(result.author) if result.author else 'N/A'}")


async def example_holdings_4_material_filter():
    """소장자료 예시 4: 자료유형 필터"""
    print("\n" + "=" * 80)
    print("소장자료 예시 4: 자료유형 필터 - 단행본만 검색")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = LibraryHoldingsSearchParams(
            query="블록체인",
            material_types=[MaterialType.BOOK],  # 단행본만
            year_range=YearRange(from_year=2019, to_year=2025),
            results_per_page=20
        )
        
        results = await scraper.execute_holdings_search(params, max_results=5)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.title}")
            print(f"    자료유형: {result.material_type or 'N/A'}")
            print(f"    ISBN: {result.isbn or 'N/A'}")


# ============================================================================
# ElectronicResourceScraper 사용 예시 (전자자료 검색)
# ============================================================================

async def example_electronic_1_simple():
    """전자자료 예시 1: 기본 검색"""
    print("\n" + "=" * 80)
    print("전자자료 예시 1: 기본 검색 - 'machine learning'")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = ElectronicSearchParams(
            query="machine learning",
            search_field=ElectronicSearchField.KEYWORD,
            results_per_page=20,
            academic_journals_only=True,  # 학술저널만
            year_range=ElectronicYearRange(from_year=2020, to_year=2025)
        )
        
        results = await scraper.execute_electronic_search(params, max_results=5)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.title}")
            print(f"    저자: {', '.join(result.author) if result.author else 'N/A'}")
            print(f"    출처: {result.source or 'N/A'}")
            print(f"    발행년도: {result.publication_year or 'N/A'}")
            print(f"    DOI: {result.doi or 'N/A'}")
            if result.abstract:
                print(f"    초록: {result.abstract[:100]}...")
            if result.keywords:
                print(f"    키워드: {', '.join(result.keywords[:5])}")
    
    logger.info("로그아웃 완료")


async def example_electronic_2_advanced():
    """전자자료 예시 2: 고급 검색"""
    print("\n" + "=" * 80)
    print("전자자료 예시 2: 고급 검색 - 'deep learning' OR 'neural networks'")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = ElectronicSearchParams(
            query="deep learning",
            search_field=ElectronicSearchField.KEYWORD,
            additional_queries=[
                ElectronicAdditionalQuery(
                    query="neural networks",
                    operator=ElectronicQueryOperator.OR
                )
            ],
            results_per_page=20,
            academic_journals_only=True,
            year_range=ElectronicYearRange(from_year=2022, to_year=2025)
        )
        
        results = await scraper.execute_electronic_search(params, max_results=10)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.title}")
            print(f"    저자: {', '.join(result.author) if result.author else 'N/A'}")
            print(f"    발행년도: {result.publication_year or 'N/A'}")


async def example_electronic_3_field_specific():
    """전자자료 예시 3: 필드별 검색"""
    print("\n" + "=" * 80)
    print("전자자료 예시 3: 필드별 검색 - 제목='artificial intelligence' AND 주제='ethics'")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = ElectronicSearchParams(
            query="artificial intelligence",
            search_field=ElectronicSearchField.TITLE,
            additional_queries=[
                ElectronicAdditionalQuery(
                    search_field=ElectronicSearchField.SUBJECT,
                    query="ethics",
                    operator=ElectronicQueryOperator.AND
                )
            ],
            results_per_page=20,
            academic_journals_only=True,
            year_range=ElectronicYearRange(from_year=2021, to_year=2025)
        )
        
        results = await scraper.execute_electronic_search(params, max_results=5)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n[{i}] {result.title}")
            print(f"    키워드: {', '.join(result.keywords) if result.keywords else 'N/A'}")


async def example_electronic_4_with_details():
    """전자자료 예시 4: 상세 정보 포함 검색"""
    print("\n" + "=" * 80)
    print("전자자료 예시 4: 상세 정보 포함 (초록, 키워드 등)")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
        logger.info("로그인 성공! 검색 시작...")
        
        params = ElectronicSearchParams(
            query="quantum computing",
            search_field=ElectronicSearchField.KEYWORD,
            results_per_page=10,
            academic_journals_only=True,
            year_range=ElectronicYearRange(from_year=2023, to_year=2025)
        )
        
        # execute_electronic_search는 자동으로 각 결과의 상세 정보를 가져옴
        results = await scraper.execute_electronic_search(params, max_results=3)
        
        logger.info(f"검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"\n{'=' * 80}")
            print(f"[{i}] {result.title}")
            print(f"{'=' * 80}")
            print(f"저자: {', '.join(result.author) if result.author else 'N/A'}")
            print(f"출처: {result.source or 'N/A'}")
            print(f"발행년도: {result.publication_year or 'N/A'}")
            print(f"DOI: {result.doi or 'N/A'}")
            print(f"링크: {result.link_url or 'N/A'}")
            
            if result.abstract:
                print(f"\n초록:")
                print(f"  {result.abstract[:300]}...")
            
            if result.keywords:
                print(f"\n키워드:")
                print(f"  {', '.join(result.keywords)}")


# ============================================================================
# 통합 검색 예시
# ============================================================================

async def example_combined_search():
    """통합 예시: 소장자료와 전자자료 동시 검색"""
    print("\n" + "=" * 80)
    print("통합 예시: '클라우드 컴퓨팅' - 소장자료 + 전자자료 동시 검색")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        logger.error("환경변수 YONSEI_ID, YONSEI_PW가 필요합니다")
        return
    
    query = "클라우드 컴퓨팅"
    year_range = (2020, 2025)
    
    # 소장자료 검색
    print("\n--- 소장자료 검색 ---")
    async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as holdings_scraper:
        holdings_params = LibraryHoldingsSearchParams(
            query=query,
            year_range=YearRange(from_year=year_range[0], to_year=year_range[1]),
            results_per_page=20
        )
        holdings_results = await holdings_scraper.execute_holdings_search(
            holdings_params, 
            max_results=5
        )
        
        logger.info(f"소장자료 검색 결과: {len(holdings_results)}건")
        for i, result in enumerate(holdings_results, 1):
            print(f"  {i}. {result.title} ({result.publication_year})")
    
    # 전자자료 검색
    print("\n--- 전자자료 검색 ---")
    async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as electronic_scraper:
        electronic_params = ElectronicSearchParams(
            query="cloud computing",  # 영문 검색
            search_field=ElectronicSearchField.KEYWORD,
            results_per_page=20,
            academic_journals_only=True,
            year_range=ElectronicYearRange(from_year=year_range[0], to_year=year_range[1])
        )
        electronic_results = await electronic_scraper.execute_electronic_search(
            electronic_params,
            max_results=5
        )
        
        logger.info(f"전자자료 검색 결과: {len(electronic_results)}건")
        for i, result in enumerate(electronic_results, 1):
            print(f"  {i}. {result.title} ({result.publication_year})")
    
    print(f"\n총 검색 결과: {len(holdings_results) + len(electronic_results)}건")


# ============================================================================
# 메인 함수
# ============================================================================

async def main():
    """메인 함수 - 사용 예시 선택"""
    print("\n" + "=" * 80)
    print("연세대학교 도서관 스크래퍼 사용 예시")
    print("=" * 80)
    
    if not YONSEI_ID or not YONSEI_PW:
        print("\n⚠️  환경변수 설정이 필요합니다!")
        print("1. 이 디렉토리에 .env 파일 생성")
        print("2. 다음 내용 추가:")
        print("   YONSEI_ID=your_id")
        print("   YONSEI_PW=your_password")
        return
    
    print("\n사용 가능한 예시:")
    print("\n[소장자료 검색 - LibraryHoldingsScraper]")
    print("  1. 기본 검색")
    print("  2. 고급 검색 (OR/AND 조합)")
    print("  3. 필드별 검색")
    print("  4. 자료유형 필터")
    print("\n[전자자료 검색 - ElectronicResourceScraper]")
    print("  5. 기본 검색")
    print("  6. 고급 검색")
    print("  7. 필드별 검색")
    print("  8. 상세 정보 포함 검색")
    print("\n[통합 검색]")
    print("  9. 소장자료 + 전자자료 동시 검색")
    print("\n  0. 모든 예시 실행")
    
    choice = input("\n실행할 예시 번호를 선택하세요 (1-9, 0): ").strip()
    
    try:
        if choice == "1":
            await example_holdings_1_simple()
        elif choice == "2":
            await example_holdings_2_advanced()
        elif choice == "3":
            await example_holdings_3_field_specific()
        elif choice == "4":
            await example_holdings_4_material_filter()
        elif choice == "5":
            await example_electronic_1_simple()
        elif choice == "6":
            await example_electronic_2_advanced()
        elif choice == "7":
            await example_electronic_3_field_specific()
        elif choice == "8":
            await example_electronic_4_with_details()
        elif choice == "9":
            await example_combined_search()
        elif choice == "0":
            # 모든 예시 실행 (주의: 시간이 오래 걸림)
            await example_holdings_1_simple()
            await example_holdings_2_advanced()
            await example_holdings_3_field_specific()
            await example_holdings_4_material_filter()
            await example_electronic_1_simple()
            await example_electronic_2_advanced()
            await example_electronic_3_field_specific()
            await example_electronic_4_with_details()
            await example_combined_search()
        else:
            print("잘못된 선택입니다.")
    
    except Exception as e:
        logger.error(f"예시 실행 중 오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
