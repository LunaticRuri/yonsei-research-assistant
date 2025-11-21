# faiss_build.py
import sqlite3
import numpy as np
import faiss
import pickle
import os

# 현재 파일의 위치를 기준으로 프로젝트 루트(yonsei-research-assistant) 경로를 찾아 sys.path에 추가
# 현재위치 -> 상위(data) -> 상위(retrieval-service)
from pathlib import Path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from config import settings

# Metadata Database Paths
DATABASE_PATH = settings.METADATA_DB_PATH

# FAISS Index Paths
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH
FAISS_ID_TO_METADATA_PATH = settings.FAISS_ID_TO_METADATA_PATH
VECTOR_DIMENSION = settings.VECTOR_DIMENSION

# 배치 처리 설정
BATCH_SIZE = 100000  # 한 번에 처리할 레코드 수

# --- 스크립트 시작 ---
print("FAISS 인덱스 구축을 시작합니다 (배치 처리 모드).")

# 1. 전체 데이터 개수 확인
print(f"'{DATABASE_PATH}'에서 전체 데이터 개수를 확인합니다...")
with sqlite3.connect(DATABASE_PATH) as conn:
    cur = conn.cursor()
    # NOTE: 조건 추후 변경 가능! 단, 밑의 쿼리 조건도 같이 변경해야 함.
    # 검색 결과의 유의미성 보장 위해서 도서 소개글 또는 목차 길이 조건 추가
    cur.execute("""
        SELECT COUNT(*)
        FROM book_embeddings e
        JOIN books b ON e.isbn = b.isbn
        WHERE e.embedding IS NOT NULL
            AND ((LENGTH(b.intro) >= 200)
            OR (LENGTH(b.toc) >= 200))
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
            AND ((LENGTH(b.intro) >= 200)
            OR (LENGTH(b.toc) >= 200))
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
                AND ((LENGTH(b.intro) >= 200)
                OR (LENGTH(b.toc) >= 200))
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
print(f"FAISS 인덱스를 '{FAISS_INDEX_PATH}' 파일로 저장합니다...")
# 디렉토리 생성
os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
faiss.write_index(index_with_ids, FAISS_INDEX_PATH)

print(f"ISBN ID 매핑을 '{FAISS_ID_TO_METADATA_PATH}' 파일로 저장합니다...")
# FAISS 정수 ID -> 원본 TEXT isbn 로의 매핑
faiss_id_map = {i: isbn for i, isbn in enumerate(all_isbns)}
with open(FAISS_ID_TO_METADATA_PATH, 'wb') as f:
    pickle.dump(faiss_id_map, f)

print("배치 처리 방식의 인덱스 구축이 완료되었습니다.")
print(f"최종 인덱스 크기: {index_with_ids.ntotal}개")
print(f"벡터 차원: {VECTOR_DIMENSION}")
print(f"사용된 배치 크기: {BATCH_SIZE}")