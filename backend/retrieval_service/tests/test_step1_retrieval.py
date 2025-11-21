"""
Step 1 (Retrieval) 테스트 스크립트

SearchExecutor의 Step 1 (검색) 부분만 테스트합니다.
- ElectronicResourcesAdapter와 LibraryHoldingsAdapter의 검색 기능 확인
- SearchRequest → 각 어댑터별 검색 파라미터 변환 확인
- 실제 연세대 도서관 스크래핑 동작 확인
"""
import asyncio
import logging
import sys
import argparse

from shared.models import (
    SearchRequest, 
    SearchQueries,
    RetrievalRoute,
    QueryOperator,
    ElectronicSearchField,
    LibrarySearchField
)
from retrieval_service.services.retriever import RetrieverService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_electronic_resources_search():
    """전자자료 검색 테스트"""
    logger.info("=" * 80)
    logger.info("TEST 1: Electronic Resources Search")
    logger.info("=" * 80)
    
    # 검색 요청 생성
    search_request = SearchRequest(
        queries=SearchQueries(
            query_1="artificial intelligence",
            search_field_1=ElectronicSearchField.TITLE,
            operator_1=QueryOperator.AND,
            query_2="machine learning",
            search_field_2=ElectronicSearchField.TITLE
        ),
        routes=[RetrievalRoute.YONSEI_ELECTRONICS],
        filters={
            "year_range": (2020, 2024),
            "academic_journals_only": True
        },
        top_k=5,
        user_query="AI와 머신러닝에 관한 최근 학술논문"
    )
    
    logger.info(f"Search Query: {search_request.queries.query_1}")
    logger.info(f"Additional Query: {search_request.queries.query_2}")
    logger.info(f"Year Range: {search_request.filters.get('year_range')}")
    
    # Retriever 실행
    retriever = RetrieverService()
    
    try:
        documents = await retriever.retrieve_all(search_request)
        
        logger.info(f"\n✅ Retrieved {len(documents)} documents")
        
        # 결과 출력
        for i, doc in enumerate(documents[:3], 1):  # 상위 3개만 출력
            logger.info(f"\n--- Document {i} ---")
            logger.info(f"Title: {doc.metadata.get('title', 'N/A')}")
            logger.info(f"Author: {doc.metadata.get('author', 'N/A')}")
            logger.info(f"Year: {doc.metadata.get('publication_year', 'N/A')}")
            logger.info(f"DOI: {doc.metadata.get('doi', 'N/A')}")
            logger.info(f"Content Preview: {doc.content[:200]}...")
            logger.info(f"Score: {doc.score}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_library_holdings_search():
    """도서관 소장자료 검색 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Library Holdings Search")
    logger.info("=" * 80)
    
    # 검색 요청 생성
    search_request = SearchRequest(
        queries=SearchQueries(
            query_1="인공지능",
            search_field_1=LibrarySearchField.TITLE
        ),
        routes=[RetrievalRoute.YONSEI_HOLDINGS],
        filters={
            "year_range": (2020, 2024),
            "material_types": ["BOOK"]  # 단행본만
        },
        top_k=5,
        user_query="인공지능 관련 도서"
    )
    
    logger.info(f"Search Query: {search_request.queries.query_1}")
    logger.info(f"Material Types: {search_request.filters.get('material_types')}")
    
    # Retriever 실행
    retriever = RetrieverService()
    
    try:
        documents = await retriever.retrieve_all(search_request)
        
        logger.info(f"\n✅ Retrieved {len(documents)} documents")
        
        # 결과 출력
        for i, doc in enumerate(documents[:3], 1):
            logger.info(f"\n--- Document {i} ---")
            logger.info(f"Title: {doc.metadata.get('title', 'N/A')}")
            logger.info(f"Author: {doc.metadata.get('author', 'N/A')}")
            logger.info(f"Year: {doc.metadata.get('publication_year', 'N/A')}")
            logger.info(f"ISBN: {doc.metadata.get('isbn', 'N/A')}")
            logger.info(f"Material Type: {doc.metadata.get('material_type', 'N/A')}")
            logger.info(f"Content Preview: {doc.content[:200]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_vectordb_search():
    """Vector DB 검색 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Vector DB Search")
    logger.info("=" * 80)
    
    # 검색 요청 생성
    search_request = SearchRequest(
        queries=SearchQueries(
            query_1="인공지능",
            search_field_1='vector',
            operator_1=QueryOperator.AND,
            query_2="수학",
            search_field_2='vector'
        ),
        routes=[RetrievalRoute.VECTOR_DB],
        filters={
            "year_range": (2020, 2024)
        },
        top_k=5,
        user_query="AI와 수학 관련 도서"
    )
    
    logger.info(f"Search Query: {search_request.queries.query_1}")
    
    # Retriever 실행
    retriever = RetrieverService()
    
    try:
        documents = await retriever.retrieve_all(search_request)
        
        logger.info(f"\n✅ Retrieved {len(documents)} documents")
        
        # 결과 출력
        for i, doc in enumerate(documents[:3], 1):
            logger.info(f"\n--- Document {i} ---")
            logger.info(f"Title: {doc.metadata.get('title', 'N/A')}")
            logger.info(f"Year: {doc.metadata.get('publication_year', 'N/A')}")
            logger.info(f"Subjects: {doc.metadata.get('nlk_subjects', 'N/A')}")
            logger.info(f"Content Preview: {doc.content[:200]}...")
            logger.info(f"Score: {doc.score}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_multi_source_search():
    """멀티 소스 검색 테스트 (전자자료 + 소장자료 + VectorDB)"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Multi-Source Search")
    logger.info("=" * 80)
    
    # 검색 요청 생성
    search_request = SearchRequest(
        queries=SearchQueries(
            query_1="deep learning",
            search_field_1=ElectronicSearchField.TITLE
        ),
        routes=[
            RetrievalRoute.YONSEI_ELECTRONICS,
            RetrievalRoute.YONSEI_HOLDINGS,
            RetrievalRoute.VECTOR_DB
        ],
        filters={
            "year_range": (2020, 2024)
        },
        top_k=3,  # 각 소스별 3개씩
        user_query="딥러닝 관련 자료"
    )
    
    logger.info(f"Search Query: {search_request.queries.query_1}")
    logger.info(f"Routes: {[route.value for route in search_request.routes]}")
    
    # Retriever 실행
    retriever = RetrieverService()
    
    try:
        documents = await retriever.retrieve_all(search_request)
        
        logger.info(f"\n✅ Retrieved {len(documents)} documents from multiple sources")
        
        # 소스별 분류
        by_source = {}
        for doc in documents:
            source = doc.metadata.get('source', 'unknown')
            by_source.setdefault(source, []).append(doc)
        
        logger.info(f"\nDocuments by source:")
        for source, docs in by_source.items():
            logger.info(f"  - {source}: {len(docs)} documents")
        
        # 각 소스별 첫 번째 문서 출력
        for source, docs in by_source.items():
            if docs:
                doc = docs[0]
                logger.info(f"\n--- Sample from {source} ---")
                logger.info(f"Title: {doc.metadata.get('title', 'N/A')}")
                logger.info(f"Content Preview: {doc.content[:150]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def main():
    """전체 테스트 실행"""
    parser = argparse.ArgumentParser(description="Step 1 (Retrieval) 테스트 스크립트")
    parser.add_argument("--test", type=str, choices=["electronic", "library", "vector", "multi", "all"], default="all", help="실행할 테스트 선택 (기본값: all)")
    args = parser.parse_args()

    logger.info("Starting Step 1 (Retrieval) Tests\n")
    
    results = {}
    
    # Test 1: 전자자료 검색
    if args.test in ["electronic", "all"]:
        results["Electronic Resources"] = await test_electronic_resources_search()
        if args.test == "all": await asyncio.sleep(2)  # 요청 간 지연
    
    # Test 2: 도서관 소장자료 검색
    if args.test in ["library", "all"]:
        results["Library Holdings"] = await test_library_holdings_search()
        if args.test == "all": await asyncio.sleep(2)
    
    # Test 3: 벡터 DB 검색
    if args.test in ["vector", "all"]:
        results["Vector DB"] = await test_vectordb_search()
        if args.test == "all": await asyncio.sleep(2)
    
    # Test 4: 멀티 소스 검색
    if args.test in ["multi", "all"]:
        results["Multi-Source"] = await test_multi_source_search()
    
    # 결과 요약
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    if not results:
        logger.info("No tests were run.")
        return True

    all_passed = all(results.values())
    logger.info(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)