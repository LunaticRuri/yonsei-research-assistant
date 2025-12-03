from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # OpenAI 설정
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # Gemini 설정
    GEMINI_API_KEY: str = ""
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
    
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 전역 설정 인스턴스
settings = Settings()

@lru_cache
def get_settings() -> Settings:
    """
    .env 파일을 읽어 Settings 객체를 생성하고 캐시합니다.
    앱 전체에서 이 함수를 호출해도 .env 파일은 딱 한 번만 읽습니다.
    """
    return Settings()