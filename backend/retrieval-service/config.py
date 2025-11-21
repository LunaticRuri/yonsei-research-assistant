from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
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
    
    # VectorDB 설정
    FAISS_INDEX_PATH: str = "./data/faiss.index"
    VECTOR_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    VECTOR_DIMENSION: int = 1024
    
    # 학술정보원 설정
    LIBRARY_BASE_URL: str = "https://library.yonsei.ac.kr"
    LIBRARY_TIMEOUT: int = 30
    
    # Reranking 설정
    RERANK_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANK_TOP_K: int = 20  # 최종 반환 문서 수
    FUSION_METHOD: str = "rrf"  # 'rrf' | 'weighted' | 'cross_encoder'
    
    # CRAG 설정
    CRAG_LLM_MODEL: str = "gpt-4o-mini"
    CRAG_RELEVANCE_THRESHOLD: float = 0.6
    CRAG_INCORRECT_RATIO_THRESHOLD: float = 0.7  # 이 비율 넘으면 웹 검색 필요
    
    # API 키
    OPENAI_API_KEY: Optional[str] = None
    
    # 로깅
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # 👈 추가 필드 무시 (PYTHONPATH 같은 시스템 변수)
    )

settings = Settings()