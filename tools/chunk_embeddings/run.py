import sqlite3
import pickle
import argparse
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from typing import List, Tuple
import logging
import multiprocessing as mp
from multiprocessing import Pool, Queue, Manager
import signal
import sys


# TODO: 나중에 GPU 사용하도록 수정해서 실행하기, 지금은 너무 느려서 실행 불가

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_flag = mp.Value('i', 0)


def chunk_text(text: str, chunk_size: int = 100) -> List[str]:
    """
    Split text into chunks of the specified size.

    Args:
        text: Text to split
        chunk_size: Size of each chunk (number of characters)

    Returns:
        List of chunks
    """
    if not text:
        return []

    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        if chunk.strip():  # exclude empty chunks
            chunks.append(chunk)

    return chunks


def get_processed_isbns(conn: sqlite3.Connection) -> set:
    """
    Retrieve the set of already processed ISBNs.

    Args:
        conn: SQLite connection object

    Returns:
        Set of processed ISBNs
    """
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT isbn FROM book_chunk_embeddings")
    processed_isbns = {row[0] for row in cursor.fetchall()}
    logger.info(f"Number of already processed ISBNs: {len(processed_isbns)}")
    return processed_isbns


def get_unprocessed_books(conn: sqlite3.Connection, processed_isbns: set) -> List[Tuple[str, str]]:
    """
    Retrieve the list of books that have not been processed yet.

    Args:
        conn: SQLite connection object
        processed_isbns: Set of already processed ISBNs

    Returns:
        List of (isbn, doc) tuples
    """
    cursor = conn.cursor()
    cursor.execute("SELECT isbn, doc FROM book_embeddings")
    all_books = cursor.fetchall()

    unprocessed_books = [
        (isbn, doc) for isbn, doc in all_books
        if isbn not in processed_isbns
    ]

    logger.info(f"Total number of books: {len(all_books)}")
    logger.info(f"Number of books to process: {len(unprocessed_books)}")

    return unprocessed_books


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    logger.warning("\nReceived interrupt signal. Finishing current tasks and shutting down gracefully...")
    shutdown_flag.value = 1


# Global model for each worker process
_worker_model = None

def init_worker(model_name: str):
    """Initialize worker process with signal handler and load model once"""
    global _worker_model
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logger.info(f"Worker {mp.current_process().name} loading model...")
    _worker_model = SentenceTransformer(model_name)
    logger.info(f"Worker {mp.current_process().name} model loaded!")


def process_book_chunks(args: Tuple[str, str, int]) -> List[Tuple[str, str, bytes]]:
    """
    Process a single book: chunk text and generate embeddings.
    
    Args:
        args: Tuple of (isbn, doc, chunk_size)
    
    Returns:
        List of (isbn, chunk_text, embedding_blob) tuples
    """
    global _worker_model
    isbn, doc, chunk_size = args
    
    # Check shutdown flag
    if shutdown_flag.value:
        return []
    
    if not doc:
        return []
    
    try:
        # Use the pre-loaded model (loaded once per worker in init_worker)
        if _worker_model is None:
            logger.error("Model not initialized in worker!")
            return []
        
        # Split text into chunks
        chunks = chunk_text(doc, chunk_size)
        
        if not chunks:
            return []
        
        # Generate embeddings
        embeddings = _worker_model.encode(chunks, show_progress_bar=False)
        
        # Prepare results
        results = []
        for chunk_str, embedding in zip(chunks, embeddings):
            embedding_blob = pickle.dumps(embedding)
            results.append((isbn, chunk_str, embedding_blob))
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing book {isbn}: {e}")
        return []


def save_embeddings_batch(db_path: str, batch: List[Tuple[str, str, bytes]]):
    """
    Save a batch of embeddings to the database using a separate connection.
    
    Args:
        db_path: Path to the SQLite database
        batch: List of (isbn, chunk_text, embedding_blob) tuples
    """
    if not batch:
        return
    
    # Use a separate connection for writing
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO book_chunk_embeddings (isbn, doc, embedding) VALUES (?, ?, ?)",
            batch
        )
        conn.commit()
    finally:
        conn.close()


def process_books(
    db_path: str,
    chunk_size: int = 200,
    embedding_batch_size: int = 100,
    save_interval: int = 500,
    num_workers: int = None
):
    """
    Chunk book texts and process embeddings using multiprocessing.

    Args:
        db_path: Path to the SQLite database
        chunk_size: Text chunk size (number of characters)
        embedding_batch_size: Batch size for saving to DB
        save_interval: How often to log progress (in number of books)
        num_workers: Number of worker processes (default: CPU count)
    """
    if num_workers is None:
        num_workers = mp.cpu_count()
    
    logger.info(f"Using {num_workers} worker processes")
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Connect to the database
    conn = sqlite3.connect(db_path)

    try:
        # Check already processed ISBNs
        processed_isbns = get_processed_isbns(conn)

        # Get list of unprocessed books
        unprocessed_books = get_unprocessed_books(conn, processed_isbns)

        if not unprocessed_books:
            logger.info("All books have already been processed!")
            return

        conn.close()  # Close main connection before multiprocessing

        total_chunks_saved = 0
        model_name = "nlpai-lab/KURE-v1"
        
        # Prepare arguments for workers (no model_name needed anymore)
        worker_args = [
            (isbn, doc, chunk_size)
            for isbn, doc in unprocessed_books
        ]

        # Process with multiprocessing pool
        logger.info("Starting multiprocessing pool...")
        
        try:
            # Initialize workers with model loaded once per worker
            with Pool(processes=num_workers, initializer=init_worker, initargs=(model_name,)) as pool:
                # Use imap_unordered for better performance
                results_iter = pool.imap_unordered(
                    process_book_chunks,
                    worker_args,
                    chunksize=1  # 적절한 청크 크기 설정
                )
                
                # Process results and save in batches
                save_batch = []
                
                with tqdm(total=len(unprocessed_books), desc="Processing books") as pbar:
                    for idx, chunk_embeddings in enumerate(results_iter):
                        if shutdown_flag.value:
                            logger.warning("Shutdown signal received, stopping...")
                            pool.terminate()
                            break
                        
                        # Add results to batch
                        save_batch.extend(chunk_embeddings)
                        
                        # Save when batch is large enough
                        if len(save_batch) >= embedding_batch_size:
                            save_embeddings_batch(db_path, save_batch)
                            total_chunks_saved += len(save_batch)
                            save_batch = []
                        
                        pbar.update(1)
                        
                        # Periodic status log
                        if (idx + 1) % save_interval == 0:
                            logger.info(f"Progress: {idx + 1}/{len(unprocessed_books)} books, {total_chunks_saved} chunks saved")
                
                # Save remaining batch
                if save_batch and not shutdown_flag.value:
                    save_embeddings_batch(db_path, save_batch)
                    total_chunks_saved += len(save_batch)
        
        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt received in main process. Cleaning up...")
            shutdown_flag.value = 1
        
        if shutdown_flag.value:
            logger.warning(f"Processing interrupted! Saved {total_chunks_saved} chunk embeddings before stopping.")
        else:
            logger.info(f"Processing complete! A total of {total_chunks_saved} chunk embeddings were saved.")

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise
    finally:
        if not conn:
            pass
        else:
            try:
                conn.close()
            except:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Split texts in the book_embeddings table into chunks and generate embeddings."
    )
    parser.add_argument(
        "--db-path",
        type=str,
        required=True,
        help="Path to the SQLite database file"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=200,
        help="Text chunk size (number of characters, default: 200)"
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=100,
        help="Batch size for saving to database (default: 50)"
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=500,
        help="Logging interval in number of books (default: 100)"
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=None,
        help="Number of worker processes (default: CPU count)"
    )

    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Starting Book Embedding Chunking (Multiprocessing)")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Chunk size: {args.chunk_size} characters")
    logger.info(f"Save batch size: {args.embedding_batch_size}")
    logger.info(f"Workers: {args.num_workers if args.num_workers else 'CPU count'}")
    logger.info("=" * 50)

    process_books(
        db_path=args.db_path,
        chunk_size=args.chunk_size,
        embedding_batch_size=args.embedding_batch_size,
        save_interval=args.save_interval,
        num_workers=args.num_workers
    )


if __name__ == "__main__":
    # Required for multiprocessing on macOS/Windows
    mp.set_start_method('spawn', force=True)
    main()
