from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # OpenAI 설정
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    
    # 데이터베이스 설정
    CHROMA_DB_PATH: str = "./data/chroma_db"
    
    # 서비스 URL들
    DIALOGUE_SERVICE_URL: str = "http://localhost:8001"
    STRATEGY_SERVICE_URL: str = "http://localhost:8002"
    RAG_SERVICE_URL: str = "http://localhost:8003"
    SEARCH_AGENT_SERVICE_URL: str = "http://localhost:8004"
    
    # 도서관 설정
    YONSEI_LIBRARY_BASE_URL: str = "https://library.yonsei.ac.kr"
    SCRAPING_DELAY: float = 1.0  # 요청 간 지연 시간 (초)
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    # 세션 설정
    SESSION_TIMEOUT: int = 3600  # 1시간 (초)
    
    # CORS 설정
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    # 캐싱 설정
    ENABLE_CACHING: bool = True
    CACHE_TTL: int = 300  # 5분 (초)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 전역 설정 인스턴스
settings = Settings()