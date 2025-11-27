import sqlite3
import numpy as np
import faiss
import pickle
import os

from retrieval_service.config import settings

# Embeddings Database Paths
EMBEDDINGS_DATABASE_PATH = settings.EMBEDDINGS_DB_PATH

# Metadata Database Paths
METADATA_DATABASE_PATH = settings.METADATA_DB_PATH

# FAISS Index Paths
FAISS_INDEX_PATH = settings.FAISS_INDEX_PATH
FAISS_ID_TO_METADATA_PATH = settings.FAISS_ID_TO_METADATA_PATH
VECTOR_DIMENSION = settings.VECTOR_DIMENSION

# 배치 처리 설정
BATCH_SIZE = 100000  # 한 번에 처리할 레코드 수

# --- 스크립트 시작 ---
print("FAISS 인덱스 구축을 시작합니다 (배치 처리 모드).")

# 1. 전체 데이터 개수 확인
print(f"'{EMBEDDINGS_DATABASE_PATH}'에서 전체 데이터 개수를 확인합니다...")
with sqlite3.connect(EMBEDDINGS_DATABASE_PATH) as embeddings_conn:
    embeddings_cur = embeddings_conn.cursor()
    # NOTE: 조건 추후 변경 가능! 단, 밑의 쿼리 조건도 같이 변경해야 함.
    # 검색 결과의 유의미성 보장 위해서 도서 소개글 또는 목차 길이 조건 추가
    
    embeddings_cur.execute("""
        SELECT COUNT(*)
        FROM book_embeddings
        WHERE embedding IS NOT NULL
    """)
    total_count = embeddings_cur.fetchone()[0]

if total_count == 0:
    print("데이터베이스에 임베딩 데이터가 없습니다. 스크립트를 종료합니다.")
    exit()

print(f"총 {total_count}개의 임베딩 데이터를 발견했습니다.")
print(f"배치 크기: {BATCH_SIZE}, 총 배치 수: {(total_count + BATCH_SIZE - 1) // BATCH_SIZE}")

# 2. FAISS 인덱스 초기화
print("FAISS 인덱스를 초기화합니다...")
# 첫 번째 배치로 실제 벡터 차원 확인
with sqlite3.connect(EMBEDDINGS_DATABASE_PATH) as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT embedding
        FROM book_embeddings
        WHERE embedding IS NOT NULL
        LIMIT 1
    """)
    first_blob = cur.fetchone()[0]
    first_vector = np.frombuffer(first_blob, dtype=np.float32)
    actual_dimension = first_vector.shape[0]
    
    if actual_dimension != VECTOR_DIMENSION:
        print(f"실제 벡터 차원({actual_dimension})으로 VECTOR_DIMENSION을 업데이트합니다.")
        VECTOR_DIMENSION = actual_dimension

# FAISS 인덱스 생성 변수 (루프 진입 후 첫 배치에서 초기화)
index_with_ids = None

# (ISBN, chunk_index) 매핑을 위한 리스트
all_identifiers = []

# 3. 배치 단위로 데이터 처리 및 인덱스 구축
current_id = 0
print("배치 단위로 데이터를 처리하고 FAISS 인덱스에 추가합니다...")

for batch_num in range(0, total_count, BATCH_SIZE):
    print(f"배치 {batch_num // BATCH_SIZE + 1}/{(total_count + BATCH_SIZE - 1) // BATCH_SIZE} 처리 중...")
    
    # 배치 데이터 로드
    with sqlite3.connect(EMBEDDINGS_DATABASE_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT isbn, chunk_index, embedding
            FROM book_embeddings
            WHERE embedding IS NOT NULL
            LIMIT ? OFFSET ?
        """, (BATCH_SIZE, batch_num))
        batch_data = cur.fetchall()
    
    if not batch_data:
        break
    
    # 배치 데이터 처리
    batch_identifiers = [(row[0], row[1]) for row in batch_data]  # (isbn, chunk_index) tuples
    batch_embedding_blobs = [row[2] for row in batch_data]
    
    # BLOB을 NumPy 배열로 변환
    batch_embedding_vectors = []
    for blob in batch_embedding_blobs:
        vector = np.frombuffer(blob, dtype=np.float32)
        batch_embedding_vectors.append(vector)
    
    # 배치 매트릭스 생성
    batch_embeddings_matrix = np.vstack(batch_embedding_vectors)
    
    # 인덱스 초기화 및 학습 (첫 번째 배치에서 수행)
    if index_with_ids is None:
        print("메모리 최적화를 위해 ScalarQuantizer(QT_8bit) 인덱스를 생성하고 학습합니다...")
        # QT_8bit: float32(4byte) -> 1byte로 압축하여 메모리 1/4 절약
        quantizer = faiss.IndexScalarQuantizer(VECTOR_DIMENSION, faiss.ScalarQuantizer.QT_8bit)
        
        # Quantizer는 데이터 분포 학습이 필요함
        quantizer.train(batch_embeddings_matrix)
        
        index_with_ids = faiss.IndexIDMap(quantizer)

    # FAISS 인덱스에 추가
    batch_faiss_ids = np.arange(current_id, current_id + len(batch_identifiers))
    index_with_ids.add_with_ids(batch_embeddings_matrix, batch_faiss_ids)
    
    # (ISBN, chunk_index) 매핑 저장
    all_identifiers.extend(batch_identifiers)
    current_id += len(batch_identifiers)
    
    print(f"  - {len(batch_identifiers)}개 벡터 추가됨 (누적: {current_id}개)")

print(f"총 {index_with_ids.ntotal}개의 벡터가 인덱스에 성공적으로 추가되었습니다.")

# 4. FAISS 인덱스와 ID 맵 저장
print(f"FAISS 인덱스를 '{FAISS_INDEX_PATH}' 파일로 저장합니다...")
# 디렉토리 생성
os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
faiss.write_index(index_with_ids, FAISS_INDEX_PATH)

print(f"(ISBN, chunk_index) ID 매핑을 '{FAISS_ID_TO_METADATA_PATH}' 파일로 저장합니다...")
# FAISS 정수 ID -> (isbn, chunk_index) 튜플로의 매핑
faiss_id_map = {i: identifier for i, identifier in enumerate(all_identifiers)}
with open(FAISS_ID_TO_METADATA_PATH, 'wb') as f:
    pickle.dump(faiss_id_map, f)

print("배치 처리 방식의 인덱스 구축이 완료되었습니다.")
print(f"최종 인덱스 크기: {index_with_ids.ntotal}개")
print(f"벡터 차원: {VECTOR_DIMENSION}")
print(f"사용된 배치 크기: {BATCH_SIZE}")