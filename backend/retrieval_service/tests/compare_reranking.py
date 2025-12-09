import asyncio
import json
import os
import logging
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel

# Add backend to sys.path
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from retrieval_service.config import retrieval_settings
from retrieval_service.services.retriever import RetrieverService
from retrieval_service.services.ranker import RankerService
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
RERANK_MODEL_FINETUNED = os.getenv("RERANK_MODEL_PATH")

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

async def evaluate_reranking(queries: List[Dict], top_k: int = 10):
    
    # Initialize Retriever (Shared)
    retriever = RetrieverService()
    
    # Initialize Rankers
    # 1. Random (uses default ranker but calls tmp method)
    try:
        ranker_random = RankerService()
    except Exception as e:
        logger.error(f"Failed to initialize Random Ranker (Default Model Load Failed): {e}")
        ranker_random = None
    
    # 2. Default Model
    retrieval_settings.RERANK_MODEL = RERANK_MODEL_DEFAULT
    try:
        ranker_default = RankerService()
    except Exception as e:
        logger.error(f"Failed to initialize Default Ranker ({RERANK_MODEL_DEFAULT}): {e}")
        ranker_default = None
    
    # 3. Finetuned Model
    if RERANK_MODEL_FINETUNED and os.path.exists(RERANK_MODEL_FINETUNED):
        retrieval_settings.RERANK_MODEL = RERANK_MODEL_FINETUNED
        try:
            ranker_finetuned = RankerService()
        except Exception as e:
            logger.error(f"Failed to initialize Finetuned Ranker ({RERANK_MODEL_FINETUNED}): {e}")
            ranker_finetuned = None
    else:
        logger.warning("Finetuned model path not found. Skipping finetuned model evaluation.")
        ranker_finetuned = None

    results = {
        "Random": {"hit_rate": 0, "mrr": 0, "total_queries": 0, "details": []},
        "Default": {"hit_rate": 0, "mrr": 0, "total_queries": 0, "details": []},
        "Finetuned": {"hit_rate": 0, "mrr": 0, "total_queries": 0, "details": []}
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
            # RetrievalRoute.VECTOR_DB,
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
            top_k=20, # Fetch more to rerank
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

        # 2. Apply Reranking Strategies
        methods = [
            ("Random", ranker_random, "tmp"),
            ("Default", ranker_default, "model"),
            ("Finetuned", ranker_finetuned, "model")
        ]
        
        for name, ranker, mode in methods:
            if not ranker:
                continue
                
            try:
                if mode == "tmp":
                    reranked_docs = ranker.tmp_rerank_and_fuse(raw_docs, rerank_query)
                else:
                    reranked_docs = await ranker.rerank_and_fuse(raw_docs, rerank_query)
                
                # Take top_k
                top_docs = reranked_docs[:top_k]
                
                # Evaluate
                first_relevant_rank = 0
                has_relevant = False
                
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
                if has_relevant:
                    results[name]["hit_rate"] += 1
                    results[name]["mrr"] += (1.0 / first_relevant_rank)
                
                results[name]["details"].append({
                    "query": user_query,
                    "top_docs": doc_details,
                    "hit": has_relevant,
                    "reciprocal_rank": 1.0 / first_relevant_rank if has_relevant else 0
                })
                logger.info(f"  -> [{name}] Query: {user_query} Hit: {has_relevant}, First Relevant Rank: {first_relevant_rank}")
            except Exception as e:
                logger.error(f"Reranking failed for {name}: {e}")

    # Finalize Results
    summary = []
    print("\n" + "="*60)
    print("RERANKING EVALUATION SUMMARY")
    print("="*60)
    print(f"{'Method':<15} {'Hit Rate':<10} {'MRR':<10}")
    print("-" * 60)
    
    for name, data in results.items():
        if data["total_queries"] > 0:
            avg_hit_rate = data["hit_rate"] / data["total_queries"]
            avg_mrr = data["mrr"] / data["total_queries"]
            print(f"{name:<15} {avg_hit_rate:<10.4f} {avg_mrr:<10.4f}")
            
            summary.append({
                "method": name,
                "hit_rate": avg_hit_rate,
                "mrr": avg_mrr,
                "details": data["details"]
            })
    print("="*60)
    
    # Save to file
    with open("reranking_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("Detailed results saved to reranking_evaluation_results.json")

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
    #test_queries = all_queries[10:11] 
    test_queries = all_queries
    logger.info(f"Loaded {len(all_queries)} queries. Using first {len(test_queries)} for evaluation.")
    
    await evaluate_reranking(test_queries, top_k=10)

if __name__ == "__main__":
    asyncio.run(main())

