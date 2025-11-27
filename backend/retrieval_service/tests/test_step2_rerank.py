"""
주의! 메모리 제한이 있는 환경에서는 이 스크립트를 실행하지 마세요.

Step 2 (Rerank + Fusion) 테스트 스크립트

Step 1 (Retrieval) 결과물을 바탕으로 Step 2 (Rerank + Fusion) 과정을 테스트합니다.
- RetrieverService로 문서 검색
- RankerService로 Reranking 및 Fusion 수행
- Reranking 전후의 순위 변화 및 점수 확인
"""
import asyncio
import logging
import sys
import argparse
from collections import Counter

from shared.models import (
    SearchRequest, 
    SearchQueries,
    RetrievalRoute,
    QueryOperator,
    ElectronicSearchField
)
from retrieval_service.services.retriever import RetrieverService
from retrieval_service.services.ranker import RankerService

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_rerank_basic():
    """기본 Reranking 테스트 (단일 소스)"""
    logger.info("=" * 80)
    logger.info("TEST 1: Basic Reranking (Single Source)")
    logger.info("=" * 80)
    
    # 1. 검색 요청 (Step 1)
    search_request = SearchRequest(
        queries=SearchQueries(
            query_1="도덕 의사결정",
            search_field_1=ElectronicSearchField.TOTAL,
            operator_1=QueryOperator.AND,
            query_2="윤리학",
            search_field_2=ElectronicSearchField.TOTAL,
            operator_2=QueryOperator.AND,
            query_3="철학",
            search_field_3=ElectronicSearchField.TOTAL
        ),
        routes=[RetrievalRoute.YONSEI_ELECTRONICS],
        filters={
            "year_range": (2000, 2024)
        },
        top_k=20,
        user_query="철학에서 도덕적 의사결정의 근거와 원칙은 무엇인가?"
    )
    
    retriever = RetrieverService()
    ranker = RankerService()
    
    try:
        logger.info("Step 1: Retrieving documents...")
        documents = await retriever.retrieve_all(search_request)
        logger.info(f"Retrieved {len(documents)} documents")
        
        if not documents:
            logger.warning("No documents retrieved. Skipping rerank test.")
            return False

        # 원본 순서 출력 (상위 3개)
        logger.info("\n--- Before Reranking (Top 3) ---")
        for i, doc in enumerate(documents[:3], 1):
            logger.info(f"{i}. [{doc.score:.4f}] {doc.metadata.get('title', 'N/A')}")

        # 2. Rerank 실행 (Step 2)
        logger.info("\nStep 2: Reranking documents...")
        ranked_docs = ranker.rerank_and_fuse(
            documents=documents,
            user_query=search_request.user_query
        )
        
        logger.info(f"Reranked {len(ranked_docs)} documents")
        
        # Rerank 결과 출력
        logger.info("\n--- After Reranking (Top 3) ---")
        for i, doc in enumerate(ranked_docs[:3], 1):
            logger.info(f"{doc.rank}. [Rerank Score: {doc.rerank_score:.4f}] {doc.metadata.get('title', 'N/A')}")
            logger.info(f"   (Original Score: {doc.original_score:.4f})")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

async def test_rerank_fusion_multi_source():
    """멀티 소스 Fusion 및 Reranking 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Multi-Source Fusion & Reranking")
    logger.info("=" * 80)
    
    # 1. 검색 요청 (Step 1)
    search_request = SearchRequest(
        queries=SearchQueries(
            query_1="재정 정책",
            search_field_1=ElectronicSearchField.TOTAL,
            operator_1=QueryOperator.AND,
            query_2="경제 성장",
            search_field_2=ElectronicSearchField.TOTAL
        ),
        routes=[
            RetrievalRoute.YONSEI_ELECTRONICS,
            RetrievalRoute.VECTOR_DB
        ],
        filters={
            "year_range": (2000, 2024)
        },
        top_k=10,
        user_query="재정 정책이 경제 성장에 미치는 영향은 무엇인가?"
    )
    
    retriever = RetrieverService()
    ranker = RankerService()
    
    try:
        logger.info("Step 1: Retrieving documents from multiple sources...")
        documents = await retriever.retrieve_all(search_request)
        logger.info(f"Retrieved {len(documents)} documents")
        
        # 소스별 분포 확인
        sources = [doc.metadata.get('source', 'unknown') for doc in documents]
        logger.info(f"Source distribution: {dict(Counter(sources))}")

        if not documents:
            logger.warning("No documents retrieved. Skipping fusion test.")
            return False

        # 2. Rerank & Fusion 실행 (Step 2)
        logger.info("\nStep 2: Reranking and Fusing...")
        ranked_docs = ranker.rerank_and_fuse(
            documents=documents,
            user_query=search_request.user_query,
            method="rrf" # RRF 방식 테스트
        )
        
        logger.info(f"Final ranked documents: {len(ranked_docs)}")
        
        # 결과 출력
        logger.info("\n--- Final Ranked Documents (Top 5) ---")
        for doc in ranked_docs[:5]:
            source = doc.metadata.get('source', 'unknown') or doc.source
            logger.info(f"{doc.rank}. [{source}] {doc.metadata.get('title', 'N/A')}")
            logger.info(f"   Score: {doc.rerank_score:.4f}")

        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False

async def main():
    parser = argparse.ArgumentParser(description="Step 2 (Rerank) 테스트 스크립트")
    parser.add_argument("--test", type=str, choices=["basic", "fusion", "all"], default="all", help="실행할 테스트 선택")
    args = parser.parse_args()

    logger.info("Starting Step 2 (Rerank + Fusion) Tests\n")
    
    results = {}
    
    if args.test in ["basic", "all"]:
        results["Basic Rerank"] = await test_rerank_basic()
        if args.test == "all": await asyncio.sleep(1)

    if args.test in ["fusion", "all"]:
        results["Fusion Rerank"] = await test_rerank_fusion_multi_source()

    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    if not results:
        logger.info("No tests were run.")
        return True

    return all(results.values())

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
