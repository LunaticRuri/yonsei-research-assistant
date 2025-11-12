import sqlite3
import numpy as np
import faiss
import pickle
import os
from sentence_transformers import SentenceTransformer

# --- 설정 ---

MODEL_NAME = "nlpai-lab/KURE-v1"
DATA_DIR = "/home/namu101/data"

# Database Paths
DATABASE_PATH = os.path.join(DATA_DIR, 'sh_navigator.db')

# FAISS Index Paths
BOOKS_FAISS_INDEX_PATH = os.path.join(DATA_DIR, 'faiss/book_faiss_index.faiss')
ISBN_MAP_PATH = os.path.join(DATA_DIR, 'faiss/book_isbn_map.pkl')
VECTOR_DIMENSION = 1024

# --- 초기화 ---
print("검색 시스템을 초기화합니다...")
# 1. 필요 파일 및 모델 로드
try:
    index = faiss.read_index(BOOKS_FAISS_INDEX_PATH)
    with open(ISBN_MAP_PATH, 'rb') as f:
        node_id_map = pickle.load(f)
except FileNotFoundError:
    print("오류: 인덱스 파일 또는 맵 파일이 없습니다. 먼저 build_faiss_index.py를 실행하세요.")
    exit()

print("임베딩 모델을 로드합니다...")
model = SentenceTransformer(MODEL_NAME)
con = sqlite3.connect(DATABASE_PATH)


# --- 검색 함수 ---
def search_similar_nodes_by_text(query_text, k=5):
    """주어진 텍스트와 의미적으로 유사한 노드를 k개 찾습니다."""
    print(f"\n===== 검색 시작: '{query_text}' =====")
    
    # 2. 검색 쿼리를 벡터로 변환
    query_vector = model.encode([query_text], convert_to_tensor=False)
    query_vector = np.array(query_vector, dtype=np.float32)

    # 3. FAISS에서 유사 벡터 검색 (거리, FAISS ID 반환)
    distances, faiss_ids = index.search(query_vector, k)

    if faiss_ids.size == 0 or faiss_ids[0][0] == -1:
        print("유사한 노드를 찾을 수 없습니다.")
        return []
        
    # 4. FAISS ID를 원본 node_id (TEXT)로 변환
    retrieved_faiss_ids = faiss_ids[0]
    retrieved_isbns = [node_id_map[i] for i in retrieved_faiss_ids if i in node_id_map]
    
    print(f"FAISS 결과 (상위 {len(retrieved_isbns)}개): {retrieved_isbns}")
    
    # 5. SQLite에서 최종 정보 조회
    placeholders = ','.join('?' for _ in retrieved_isbns)
    sql = f"SELECT isbn, doc FROM book_embeddings WHERE isbn IN ({placeholders})"
    
    cur = con.cursor()
    cur.execute(sql, retrieved_isbns)
    results = cur.fetchall()
    
    # FAISS가 찾아준 관련도 순서대로 결과를 재정렬
    ordered_results = sorted(results, key=lambda x: retrieved_isbns.index(x[0]))
    
    return ordered_results

# --- 실제 사용 예시 ---
if __name__ == '__main__':
    
    try:
        search_query = input("검색어를 입력하세요 (예: 데이터 과학과 머신러닝의 관계): ").strip()
        if not search_query:
            print("검색어가 비어 있습니다. 프로그램을 종료합니다.")
            exit()
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 취소되었습니다.")
        exit()

    top_nodes = search_similar_nodes_by_text(search_query, k=3)
    
    print("\n--- 최종 검색 결과 ---")
    if top_nodes:
        for i, node in enumerate(top_nodes):
            # doc이 너무 길 경우 일부만 출력
            doc_preview = (node[1][:100] + '...') if len(node[1]) > 100 else node[1]
            print(f"순위 {i+1}:")
            print(f"  - Node ID: {node[0]}")
            print(f"  - 문서 내용: {doc_preview}")
    else:
        print("검색 결과가 없습니다.")
        
    con.close() # 앱 종료 시 연결 해제