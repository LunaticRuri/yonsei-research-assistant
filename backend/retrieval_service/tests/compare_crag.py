import asyncio
import json
import os
import logging
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

from retrieval_service.config import retrieval_settings
from retrieval_service.services.retriever import RetrieverService
from retrieval_service.services.ranker import RankerService
from retrieval_service.services.refiner import RefinerService
from shared.models import SearchRequest, SearchQueries, RetrievalRoute, Document, RankedDocument

# Load environment variables
load_dotenv(verbose=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Rerank Models
RERANK_MODEL_DEFAULT = os.getenv("RERANK_MODEL_DEFAULT", "BAAI/bge-reranker-v2-m3")

class EvaluationResult(BaseModel):
    is_relevant: bool
    reason: str

async def judge_relevance(query: str, doc_content: str) -> Tuple[bool, str]:
    prompt = f"""
    너는 논문, 도서 검색 시스템의 평가자다.
    아래에서 소개하고 있는 자료가 사용자의 질문과 관련이 있는지 판단해.
    
    사용자 질문: "{query}"
    
    도서 소개:
    {doc_content[:1000]}...
    
    관련이 있으면 is_relevant 값을 true로, 관련이 없으면 false로 답변해.(is_relevant)
    간단하게 판단 이유도 함께 설명해줘.(reason)
    """
    
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema' : EvaluationResult
            }
        )
        result = response.parsed
        return result.is_relevant, result.reason
    except Exception as e:
        logger.error(f"Gemini evaluation failed: {e}")
        return False, "Evaluation failed"

async def evaluate_crag(queries: List[Dict], top_k: int = 10):
    
    # Initialize Services
    retriever = RetrieverService()
    refiner = RefinerService()
    
    # Initialize Ranker (Use Default for this experiment)
    retrieval_settings.RERANK_MODEL = RERANK_MODEL_DEFAULT
    try:
        ranker = RankerService()
    except Exception as e:
        logger.error(f"Failed to initialize Ranker ({RERANK_MODEL_DEFAULT}): {e}")
        return

    results = {
        "No_CRAG": {"precision": 0, "mrr": 0, "total_queries": 0, "details": []},
        "With_CRAG": {"precision": 0, "mrr": 0, "total_queries": 0, "details": []}
    }

    # Cache for relevance judgments: {(query, doc_content_hash): (is_relevant, reason)}
    relevance_cache = {}

    for i, q_data in enumerate(queries):
        user_query = q_data.get("user_query")
        if not user_query:
            continue
            
        logger.info(f"Processing Query {i+1}/{len(queries)}: {user_query}")
        
        # 1. Retrieve Documents (Pool)
        routes = [
            #RetrievalRoute.VECTOR_DB,
            RetrievalRoute.YONSEI_HOLDINGS,
            RetrievalRoute.YONSEI_ELECTRONICS
        ]
        
        # Use pre-generated queries from JSON
        queries_data = q_data.get("queries")
        if not queries_data:
            logger.warning(f"Skipping query '{user_query}' due to missing 'queries' field.")
            continue
            
        try:
            search_queries = SearchQueries(**queries_data)
        except Exception as e:
            logger.error(f"Failed to parse SearchQueries for '{user_query}': {e}")
            continue

        request = SearchRequest(
            queries=search_queries,
            routes=routes,
            top_k=20, # Fetch enough documents
            user_query=user_query
        )
        
        try:
            # Fetch raw documents
            raw_docs = await retriever.retrieve_all(request)
            logger.info(f"  -> Retrieved {len(raw_docs)} raw documents")
            
            if not raw_docs:
                continue

        except Exception as e:
            logger.error(f"Retrieval failed for query '{user_query}': {e}")
            continue

        # Construct query string for reranker from structured queries
        rerank_query_parts = [search_queries.query_1]
        if search_queries.query_2:
            rerank_query_parts.append(search_queries.query_2)
        if search_queries.query_3:
            rerank_query_parts.append(search_queries.query_3)
        rerank_query = " ".join(rerank_query_parts)

        # 2. Rerank Documents
        try:
            reranked_docs = await ranker.rerank_and_fuse(raw_docs, rerank_query)
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            continue

        # 3. Prepare Document Sets for Comparison
        
        # Set A: No CRAG (Just top-k from reranker)
        docs_no_crag = reranked_docs[:top_k]
        
        # Set B: With CRAG
        try:
            logger.info("  -> Applying CRAG...")
            analyzed_query = await refiner.analyze_user_query(user_query=user_query)
            crag_results = await refiner.evaluate_relevance(
                documents=reranked_docs, # Pass all reranked docs to CRAG
                analyzed_user_query=analyzed_query
            )
            filtered_docs = refiner.filter_by_quality(crag_results)
            docs_with_crag = filtered_docs[:top_k]
            logger.info(f"  -> CRAG filtered: {len(reranked_docs)} -> {len(filtered_docs)}")
        except Exception as e:
            logger.error(f"CRAG failed: {e}")
            docs_with_crag = []

        comparison_sets = [
            ("No_CRAG", docs_no_crag),
            ("With_CRAG", docs_with_crag)
        ]
        
        for name, top_docs in comparison_sets:
            if not top_docs and name == "With_CRAG":
                 # If CRAG filtered everything out, it's a valid result (0 hits), but we need to handle empty list
                 pass

            # Evaluate
            first_relevant_rank = 0
            has_relevant = False
            relevant_count = 0
            
            doc_details = []
            
            for rank, doc in enumerate(top_docs, 1):
                # Check cache
                doc_hash = hash(doc.content[:100]) # Simple hash for cache key
                cache_key = (user_query, doc_hash)
                
                if cache_key in relevance_cache:
                    is_relevant, reason = relevance_cache[cache_key]
                else:
                    is_relevant, reason = await judge_relevance(user_query, doc.content)
                    relevance_cache[cache_key] = (is_relevant, reason)
                
                if is_relevant:
                    has_relevant = True
                    relevant_count += 1
                    if first_relevant_rank == 0:
                        first_relevant_rank = rank
                
                doc_details.append({
                    "rank": rank,
                    "title": doc.metadata.get('title'),
                    "is_relevant": is_relevant,
                    "reason": reason
                })
            
            # Update Metrics
            results[name]["total_queries"] += 1
            
            precision = relevant_count / len(top_docs) if top_docs else 0
            results[name]["precision"] += precision
            
            if has_relevant:
                results[name]["mrr"] += (1.0 / first_relevant_rank)
            
            results[name]["details"].append({
                "query": user_query,
                "top_docs": doc_details,
                "precision": precision,
                "reciprocal_rank": 1.0 / first_relevant_rank if has_relevant else 0
            })
            logger.info(f"  -> [{name}] Precision: {precision:.4f}, MRR: {1.0/first_relevant_rank if has_relevant else 0:.4f}")

    # Finalize Results
    summary = []
    print("\n" + "="*60)
    print("CRAG EVALUATION SUMMARY")
    print("="*60)
    print(f"{'Method':<15} {'Avg Precision':<15} {'MRR':<10}")
    print("-" * 60)
    
    for name, data in results.items():
        if data["total_queries"] > 0:
            avg_precision = data["precision"] / data["total_queries"]
            avg_mrr = data["mrr"] / data["total_queries"]
            print(f"{name:<15} {avg_precision:<15.4f} {avg_mrr:<10.4f}")
            
            summary.append({
                "method": name,
                "avg_precision": avg_precision,
                "mrr": avg_mrr,
                "details": data["details"]
            })
    print("="*60)
    
    # Save to file
    with open("crag_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("Detailed results saved to crag_evaluation_results.json")

async def main():
    # Load Queries
    json_path = os.getenv("TEST_QUERY_PATH")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            all_queries = json.load(f)
    except FileNotFoundError:
        logger.error(f"Query file not found at {json_path}")
        return

    # Use a subset for testing (e.g., first 5 for speed, or all)
    # test_queries = all_queries[12:13] 
    test_queries = all_queries
    logger.info(f"Loaded {len(all_queries)} queries. Using first {len(test_queries)} for evaluation.")
    
    await evaluate_crag(test_queries, top_k=10)

if __name__ == "__main__":
    asyncio.run(main())
