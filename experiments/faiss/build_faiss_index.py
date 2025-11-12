# faiss_build.py
import sqlite3
import numpy as np
import faiss
import pickle
import os

# --- 설정 ---  
DATA_DIR = "/home/namu101/data"

# Database Paths
DATABASE_PATH = os.path.join(DATA_DIR, 'sh_navigator.db')

# FAISS Index Paths
BOOKS_FAISS_INDEX_PATH = os.path.join(DATA_DIR, 'faiss/book_faiss_index.faiss')
ISBN_MAP_PATH = os.path.join(DATA_DIR, 'faiss/book_isbn_map.pkl')
VECTOR_DIMENSION = 1024

# 배치 처리 설정
BATCH_SIZE = 100000  # 한 번에 처리할 레코드 수

# --- 스크립트 시작 ---

print("FAISS 인덱스 구축을 시작합니다 (배치 처리 모드).")

# 1. 전체 데이터 개수 확인
print(f"'{DATABASE_PATH}'에서 전체 데이터 개수를 확인합니다...")
with sqlite3.connect(DATABASE_PATH) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM book_embeddings e
        JOIN books b ON e.isbn = b.isbn
        WHERE e.embedding IS NOT NULL
            AND ((LENGTH(b.intro) >= 100)
            OR (LENGTH(b.toc) >= 100))
    """)
    total_count = cur.fetchone()[0]

if total_count == 0:
    print("데이터베이스에 임베딩 데이터가 없습니다. 스크립트를 종료합니다.")
    exit()

print(f"총 {total_count}개의 임베딩 데이터를 발견했습니다.")
print(f"배치 크기: {BATCH_SIZE}, 총 배치 수: {(total_count + BATCH_SIZE - 1) // BATCH_SIZE}")

# 2. FAISS 인덱스 초기화
print("FAISS 인덱스를 초기화합니다...")
# 첫 번째 배치로 실제 벡터 차원 확인
with sqlite3.connect(DATABASE_PATH) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT e.embedding
        FROM book_embeddings e
        JOIN books b ON e.isbn = b.isbn
        WHERE e.embedding IS NOT NULL
            AND ((LENGTH(b.intro) >= 100)
            OR (LENGTH(b.toc) >= 100))
        LIMIT 1
    """)
    first_blob = cur.fetchone()[0]
    first_vector = np.frombuffer(first_blob, dtype=np.float32)
    actual_dimension = first_vector.shape[0]
    
    if actual_dimension != VECTOR_DIMENSION:
        print(f"실제 벡터 차원({actual_dimension})으로 VECTOR_DIMENSION을 업데이트합니다.")
        VECTOR_DIMENSION = actual_dimension

# FAISS 인덱스 생성
index = faiss.IndexFlatL2(VECTOR_DIMENSION)
index_with_ids = faiss.IndexIDMap(index)

# ISBN 매핑을 위한 리스트
all_isbns = []

# 3. 배치 단위로 데이터 처리 및 인덱스 구축
current_id = 0
print("배치 단위로 데이터를 처리하고 FAISS 인덱스에 추가합니다...")

for batch_num in range(0, total_count, BATCH_SIZE):
    print(f"배치 {batch_num // BATCH_SIZE + 1}/{(total_count + BATCH_SIZE - 1) // BATCH_SIZE} 처리 중...")
    
    # 배치 데이터 로드
    with sqlite3.connect(DATABASE_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.isbn, e.embedding
            FROM book_embeddings e
            JOIN books b ON e.isbn = b.isbn
            WHERE e.embedding IS NOT NULL
                AND ((LENGTH(b.intro) >= 100)
                OR (LENGTH(b.toc) >= 100))
            LIMIT ? OFFSET ?
        """, (BATCH_SIZE, batch_num))
        batch_data = cur.fetchall()
    
    if not batch_data:
        break
    
    # 배치 데이터 처리
    batch_isbns = [row[0] for row in batch_data]
    batch_embedding_blobs = [row[1] for row in batch_data]
    
    # BLOB을 NumPy 배열로 변환
    batch_embedding_vectors = []
    for blob in batch_embedding_blobs:
        vector = np.frombuffer(blob, dtype=np.float32)
        batch_embedding_vectors.append(vector)
    
    # 배치 매트릭스 생성
    batch_embeddings_matrix = np.vstack(batch_embedding_vectors)
    
    # FAISS 인덱스에 추가
    batch_faiss_ids = np.arange(current_id, current_id + len(batch_isbns))
    index_with_ids.add_with_ids(batch_embeddings_matrix, batch_faiss_ids)
    
    # ISBN 매핑 저장
    all_isbns.extend(batch_isbns)
    current_id += len(batch_isbns)
    
    print(f"  - {len(batch_isbns)}개 벡터 추가됨 (누적: {current_id}개)")

print(f"총 {index_with_ids.ntotal}개의 벡터가 인덱스에 성공적으로 추가되었습니다.")

# 4. FAISS 인덱스와 ID 맵 저장
print(f"FAISS 인덱스를 '{BOOKS_FAISS_INDEX_PATH}' 파일로 저장합니다...")
# 디렉토리 생성
os.makedirs(os.path.dirname(BOOKS_FAISS_INDEX_PATH), exist_ok=True)
faiss.write_index(index_with_ids, BOOKS_FAISS_INDEX_PATH)

print(f"ISBN ID 매핑을 '{ISBN_MAP_PATH}' 파일로 저장합니다...")
# FAISS 정수 ID -> 원본 TEXT isbn 로의 매핑
node_id_map = {i: isbn for i, isbn in enumerate(all_isbns)}
with open(ISBN_MAP_PATH, 'wb') as f:
    pickle.dump(node_id_map, f)

print("배치 처리 방식의 인덱스 구축이 완료되었습니다.")
print(f"최종 인덱스 크기: {index_with_ids.ntotal}개")
print(f"벡터 차원: {VECTOR_DIMENSION}")
print(f"사용된 배치 크기: {BATCH_SIZE}")