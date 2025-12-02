import sqlite3
import os
from sentence_transformers import SentenceTransformer
import torch
from tqdm import tqdm
import numpy as np

# Configuration
SOURCE_DB_PATH = "./data/book_docs.db" 
MODEL_NAME = "nlpai-lab/KURE-v1"

# Performance Tuning
# GPU 메모리가 넉넉하다면 이 값들을 늘려 속도를 높일 수 있습니다.
ENCODE_BATCH_SIZE = 512     # model.encode 내부 배치 사이즈 (기본값 32)
PROCESSING_BATCH_SIZE = 2048 # 한 번에 인코딩/DB저장할 청크의 누적 개수

# Output configurations
'''
OUTPUT_CONFIGS = [
    {
        "filename": "book_embeddings_200.db",
        "table_name": "book_embeddings_200",
        "chunk_size": 200,
        "overlap": 0
    },
    {
        "filename": "book_embeddings_200_overlap_50.db",
        "table_name": "book_embeddings_200",
        "chunk_size": 200,
        "overlap": 50
    }
]
'''
OUTPUT_CONFIGS = [
    {
        "filename": "book_embeddings_200_overlap_50.db",
        "table_name": "book_embeddings_200",
        "chunk_size": 200,
        "overlap": 50
    }
]


def get_db_connection(db_path):
    return sqlite3.connect(db_path)

def create_table(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            "isbn"	TEXT,
            "chunk_index" INTEGER,
            "doc"	TEXT,
            "embedding"	BLOB,
            PRIMARY KEY("isbn", "chunk_index")
        )
    """)
    conn.commit()

def get_processed_isbns(db_path, table_name):
    """
    이미 처리된 ISBN 목록을 가져오기
    Spot Instance 중단 시 재시작할 때 중복 처리를 방지하기 위함
    """
    if not os.path.exists(db_path):
        return set()
    
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone() is None:
            conn.close()
            return set()
            
        cursor.execute(f"SELECT DISTINCT isbn FROM {table_name}")
        isbns = {row[0] for row in cursor.fetchall()}
        conn.close()
        return isbns
    except sqlite3.Error:
        return set()

def chunk_text(text, chunk_size, overlap):
    """
    텍스트를 주어진 크기와 겹침(overlap)으로 분할
    """
    if not text:
        return []
    
    step = chunk_size - overlap
    if step <= 0:
        raise ValueError("Overlap must be smaller than chunk size")
        
    chunks = []
    text_len = len(text)
    
    if text_len <= chunk_size:
        return [text]
        
    for i in range(0, text_len, step):
        chunk = text[i:i+chunk_size]
        chunks.append(chunk)
        
        # If this chunk reaches the end of text, stop
        if i + chunk_size >= text_len:
            break
            
    return chunks

def main():
    # Check source DB
    if not os.path.exists(SOURCE_DB_PATH):
        print(f"Error: Source database '{SOURCE_DB_PATH}' not found.")
        print("Please update SOURCE_DB_PATH in the script to point to your existing sqlite database.")
        return

    # Load Model
    print(f"Loading model: {MODEL_NAME}")
    
    if torch.cuda.is_available():
        device = 'cuda'
    elif torch.backends.mps.is_available():
        device = 'mps'
    else:
        device = 'cpu'
        
    print(f"Using device: {device}")
    
    try:
        model = SentenceTransformer(MODEL_NAME, device=device)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # Read Source Data
    print("Reading source data...")
    try:
        src_conn = get_db_connection(SOURCE_DB_PATH)
        src_cursor = src_conn.cursor()
        src_cursor.execute("SELECT isbn, doc FROM book_docs")
        all_data = src_cursor.fetchall()
        src_conn.close()
    except sqlite3.Error as e:
        print(f"Error reading source database: {e}")
        return

    print(f"Total records in source: {len(all_data)}")

    # Process for each configuration
    for config in OUTPUT_CONFIGS:
        target_db = config["filename"]
        table_name = config["table_name"]
        chunk_size = config["chunk_size"]
        overlap = config["overlap"]
        
        print(f"\nProcessing: {target_db} (Chunk: {chunk_size}, Overlap: {overlap})")
        
        # Get already processed ISBNs
        processed_isbns = get_processed_isbns(target_db, table_name)
        print(f"Already processed: {len(processed_isbns)}")
        
        # Filter data
        data_to_process = [row for row in all_data if row[0] not in processed_isbns]
        print(f"Remaining to process: {len(data_to_process)}")
        
        if not data_to_process:
            print("All data already processed for this configuration.")
            continue
            
        # Connect to target DB
        tgt_conn = get_db_connection(target_db)
        create_table(tgt_conn, table_name)
        
        # Buffers for batch processing
        chunk_buffer = [] # List of text chunks
        meta_buffer = []  # List of (isbn, chunk_index) tuples
        
        # Process in loop
        # We accumulate chunks and process in batches to utilize GPU better
        for isbn, doc in tqdm(data_to_process, desc="Embedding"):
            if not doc:
                continue

            if len(doc) < 100:
                continue
                
            try:
                chunks = chunk_text(doc, chunk_size, overlap)
                if not chunks:
                    continue
                
                # Add chunks to buffer
                for i, chunk in enumerate(chunks):
                    chunk_buffer.append(chunk)
                    meta_buffer.append((isbn, i))
                
                # If buffer is full enough, process
                if len(chunk_buffer) >= PROCESSING_BATCH_SIZE:
                    # Encode
                    embeddings = model.encode(chunk_buffer, batch_size=ENCODE_BATCH_SIZE, convert_to_numpy=True, show_progress_bar=True)
                    
                    rows = []
                    for (isbn_val, chunk_idx), chunk_text_val, emb in zip(meta_buffer, chunk_buffer, embeddings):
                        rows.append((isbn_val, chunk_idx, chunk_text_val, emb.tobytes()))
                    
                    tgt_conn.executemany(f"INSERT OR REPLACE INTO {table_name} (isbn, chunk_index, doc, embedding) VALUES (?, ?, ?, ?)", rows)
                    tgt_conn.commit()
                    
                    # Clear buffers
                    chunk_buffer = []
                    meta_buffer = []
                
            except Exception as e:
                print(f"Error processing ISBN {isbn}: {e}")
                # Continue to next book
                continue
        
        # Process remaining chunks in buffer
        if chunk_buffer:
            try:
                embeddings = model.encode(chunk_buffer, batch_size=ENCODE_BATCH_SIZE, convert_to_numpy=True, show_progress_bar=True)
                
                rows = []
                for (isbn_val, chunk_idx), chunk_text_val, emb in zip(meta_buffer, chunk_buffer, embeddings):
                    rows.append((isbn_val, chunk_idx, chunk_text_val, emb.tobytes()))
                
                tgt_conn.executemany(f"INSERT OR REPLACE INTO {table_name} (isbn, chunk_index, doc, embedding) VALUES (?, ?, ?, ?)", rows)
                tgt_conn.commit()
            except Exception as e:
                print(f"Error processing remaining chunks: {e}")

        tgt_conn.close()
        print(f"Completed {target_db}")

if __name__ == "__main__":
    main()
