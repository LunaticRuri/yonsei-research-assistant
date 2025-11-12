import faiss
import sqlite3
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from typing import List, Optional

# (임베딩 모델 로드, FAISS 인덱스 로드 등은 동일)
# embeddings_model = ...
faiss_index = faiss.read_index("path/to/your.index")
db_path = "path/to/your.db"

class SqlFilteringRetriever(BaseRetriever):
    
    # 이 리트리버가 SQL 필터를 적용하도록 설정
    def __init__(self, k_results=5, pre_fetch_k=100):
        super().__init__()
        self.k_results = k_results      # 최종 반환 개수
        self.pre_fetch_k = pre_fetch_k  # FAISS에서 미리 가져올 후보군 개수

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun, 
        sql_filter: Optional[str] = None # SQL 필터(WHERE 절)를 인자로 받음
    ) -> List[Document]:
        
        # 1. 쿼리 벡터 변환
        query_vector = embeddings_model.embed_query(query)
        import numpy as np
        query_vector_np = np.array([query_vector], dtype=np.float32)

        # 2. FAISS에서 후보군 검색 (넉넉하게 K=100)
        distances, indices = faiss_index.search(query_vector_np, self.pre_fetch_k)
        
        # 3. SQLite DB 쿼리 준비
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # FAISS 결과 ID 목록
        candidate_ids = [int(doc_id) for doc_id in indices[0]]
        # 쿼리 플레이스홀더 준비 (e.g., "?,?,?,?")
        placeholders = ",".join(["?"] * len(candidate_ids))

        # --- 기본 SQL 쿼리 (ID 목록으로 필터링) ---
        base_sql = f"SELECT text_content, metadata_json FROM documents WHERE id IN ({placeholders})"
        
        # --- 사용자가 SQL 필터를 제공한 경우 ---
        if sql_filter:
            # 예: sql_filter = "category = 'news' AND date > '2024-01-01'"
            # (주의: SQL Injection 방지를 위해 실제로는 파라미터 바인딩 필요)
            final_sql = f"{base_sql} AND ({sql_filter})"
        else:
            final_sql = base_sql
            
        # 파라미터는 ID 목록
        params = tuple(candidate_ids)
        
        # (만약 sql_filter에도 파라미터가 있다면 params에 추가해야 함)

        # 4. DB에서 최종 결과 조회
        cursor.execute(final_sql, params)
        
        retrieved_docs = []
        # K=100개를 다 가져오되, 최종 반환은 k_results 만큼만
        for row in cursor.fetchall():
            if len(retrieved_docs) >= self.k_results:
                break
                
            text, metadata_str = row
            import json
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            retrieved_docs.append(
                Document(page_content=text, metadata=metadata)
            )
        
        conn.close()
        
        return retrieved_docs

# --- 사용 예시 ---
# retriever = SqlFilteringRetriever(k_results=5, pre_fetch_k=100)

# 1. 필터 없이 검색
# results = retriever.invoke("검색할 쿼리")

# 2. SQL 필터를 포함하여 검색
# (metadata_json 안의 'category' 키를 사용한다고 가정)
# sql_where_clause = "json_extract(metadata_json, '$.category') = 'tech'"
# results_filtered = retriever.invoke("기술 관련 쿼리", sql_filter=sql_where_clause)