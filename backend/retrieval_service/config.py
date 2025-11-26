from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일 로드

class Settings(BaseSettings):
    """Retrieval Service 설정"""
    
    # 연세대학교 계정 (스크래핑용)
    YONSEI_ID: str = os.getenv("YONSEI_ID")
    YONSEI_PW: str = os.getenv("YONSEI_PW")

    # 서비스 기본 정보
    SERVICE_NAME: str = "retrieval-service"
    SERVICE_PORT: int = 8003
    
    # VectorDB (FAISS + Sqlite3) 설정
    # NOTE: 실험할 때 적절하게 경로 수정
    FAISS_INDEX_PATH: str | None = os.getenv("FAISS_INDEX_PATH")
    FAISS_ID_TO_METADATA_PATH: str | None = os.getenv("FAISS_ID_TO_METADATA_PATH")
    METADATA_DB_PATH: str | None = os.getenv("METADATA_DB_PATH")
    EMBEDDINGS_DB_PATH: str | None = os.getenv("EMBEDDINGS_DB_PATH")
    EMBEDDINGS_DB_TABLE: str = "book_embeddings"

    # 임베딩 모델 설정
    VECTOR_EMBEDDING_MODEL: str = "nlpai-lab/KURE-v1"
    VECTOR_DIMENSION: int = 1024
    
    # 학술정보원 설정
    # TODO: config.py로 설정할 필요 있음
    LIBRARY_BASE_URL: str = "https://library.yonsei.ac.kr"
    LIBRARY_TIMEOUT: int = 10
    
    # Reranking 설정
    # TODO: 구현되면 나중에 수정해야 함.
    RERANK_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANK_TOP_K: int = 20  # 최종 반환 문서 수
    FUSION_METHOD: str = "rrf"  # 'rrf' | 'weighted' | 'cross_encoder'
    
    # CRAG 설정
    # TODO: 구현되면 나중에 수정해야 함.
    CRAG_LLM_MODEL: str = "gemini-1.5-flash"
    CRAG_RELEVANCE_THRESHOLD: float = 0.6
    CRAG_INCORRECT_RATIO_THRESHOLD: float = 0.7  # 이 비율 넘으면 웹 검색 필요
    
    # API 키
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    
    # 로깅
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()