import asyncio
import json
import os
import logging

from typing import List, Dict, Tuple
from dotenv import load_dotenv
from google import genai

from retrieval_service.config import retrieval_settings
from retrieval_service.adapters.vectordb_adapter import VectorDBAdapter
from shared.models import SearchRequest, SearchQueries, RetrievalRoute

from pydantic import BaseModel

# Load environment variables
load_dotenv(verbose=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)


class EvaluationResult(BaseModel):
    is_relevant: bool
    reason: str

async def judge_relevance(query: str, doc_content: str) -> Tuple[bool, str]:
    
    prompt = f"""
    너는 도서 벡터 검색 시스템의 평가자다.
    아래에서 소개하고 있는 도서가 사용자의 질문과 관련이 있는지 판단해.
    
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
        logger.info(f"Judged relevance: {result.is_relevant}, Reason: {result.reason}")
        return result.is_relevant, result.reason
    except Exception as e:
        logger.error(f"Gemini evaluation failed: {e}")
        return False, "Evaluation failed"

async def evaluate_index(index_name: str, index_path: str, metadata_path: str, queries: List[Dict], top_k: int = 20):
    """
    Evaluate a specific FAISS index.
    """
    logger.info(f"Starting evaluation for: {index_name}")
    
    if not index_path or not os.path.exists(index_path):
        logger.error(f"Index path not found: {index_path}")
        return None
    
    if not metadata_path or not os.path.exists(metadata_path):
        logger.error(f"Metadata path not found: {metadata_path}")
        return None

    # Patch settings
    retrieval_settings.FAISS_INDEX_PATH = index_path
    retrieval_settings.FAISS_ID_TO_METADATA_PATH = metadata_path
    
    # Initialize Adapter
    try:
        adapter = VectorDBAdapter()
        if not adapter.is_faiss_initialized:
            logger.error(f"Failed to initialize FAISS for {index_name}")
            return None
    except Exception as e:
        logger.error(f"Error initializing adapter for {index_name}: {e}")
        return None

    total_relevant_count = 0
    query_count = 0
    
    results = []

    for i, q_data in enumerate(queries):
        user_query = q_data.get("user_query")
        if not user_query:
            continue
            
        logger.info(f"[{index_name}] Processing Query {i+1}/{len(queries)}: {user_query}")
        
        # Create SearchRequest
        request = SearchRequest(
            queries=SearchQueries(query_1=user_query, search_field_1="vector"),
            routes=[RetrievalRoute.VECTOR_DB],
            top_k=top_k,
            user_query=user_query
        )
        
        # Search
        try:
            search_params = await adapter.request_to_search_params(request)
            documents = await adapter.search(search_params, top_k=top_k)
        except Exception as e:
            logger.error(f"Search failed for query '{user_query}': {e}")
            continue
            
        # Evaluate
        relevant_in_top_k = 0
        doc_details = []
        for doc in documents:
            is_relevant, reason = await judge_relevance(user_query, doc.content)
            if is_relevant:
                relevant_in_top_k += 1
            
            doc_details.append({
                "title": doc.metadata.get('title'),
                "is_relevant": is_relevant,
                "reason": reason
            })
        
        logger.info(f"  -> Found {relevant_in_top_k} relevant docs in top {top_k}")
        
        total_relevant_count += relevant_in_top_k
        query_count += 1
        
        results.append({
            "query": user_query,
            "relevant_count": relevant_in_top_k,
            "retrieved_docs": doc_details
        })

    avg_relevant = total_relevant_count / query_count if query_count > 0 else 0
    logger.info(f"Finished {index_name}. Average Relevant Docs @ {top_k}: {avg_relevant:.2f}")
    
    return {
        "index_name": index_name,
        "avg_relevant_at_20": avg_relevant,
        "details": results
    }

async def main():
    # Load Queries
    json_path = os.getenv("TEST_QUERY_PATH")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            all_queries = json.load(f)
    except FileNotFoundError:
        logger.error(f"Query file not found at {json_path}")
        return

    # Use a subset for testing (e.g., first 10)
    # test_queries = all_queries[30:31]
    test_queries = all_queries
    logger.info(f"Loaded {len(all_queries)} queries. Using first {len(test_queries)} for evaluation.")

    # Define Configurations
    configs = [
        {
            "name": "Original",
            "index_path": os.getenv("FAISS_INDEX_ORIG_PATH"),
            "metadata_path": os.getenv("FAISS_ID_TO_METADATA_ORIG_PATH")
        },
        {
            "name": "Chunk 200",
            "index_path": os.getenv("FAISS_INDEX_200_PATH"),
            "metadata_path": os.getenv("FAISS_ID_TO_METADATA_200_PATH")
        },
        {
            "name": "Chunk 200 (Overlap 50)",
            "index_path": os.getenv("FAISS_INDEX_200_50_PATH"),
            "metadata_path": os.getenv("FAISS_ID_TO_METADATA_200_50_PATH")
        }
    ]

    final_results = []

    for config in configs:
        if config["index_path"]:
            result = await evaluate_index(
                config["name"], 
                config["index_path"], 
                config["metadata_path"], 
                test_queries
            )
            if result:
                final_results.append(result)
        else:
            logger.warning(f"Skipping {config['name']} due to missing environment variables.")

    # Print Summary
    print("\n" + "="*50)
    print("EVALUATION SUMMARY (Average Relevant Docs @ 20)")
    print("="*50)
    for res in final_results:
        print(f"{res['index_name']}: {res['avg_relevant_at_20']:.2f}")
    print("="*50)

    # Save detailed results
    with open("evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    print("Detailed results saved to evaluation_results.json")

if __name__ == "__main__":
    asyncio.run(main())
