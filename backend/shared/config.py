from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv
from typing import ClassVar
import logging

load_dotenv()


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # lora 모델 경로 설정
    LORA_MODEL_PATH: str = os.getenv("LORA_MODEL_PATH")
    
    # OpenAI 설정
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = "gpt-4o"

    # Gemini 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-2.5-pro"
    
    # 서비스 이름 및 호스트 설정
    CLI_SERVICE_NAME: str = "cli_service"
    DIALOGUE_SERVICE_NAME: str = "dialogue_service"
    STRATEGY_SERVICE_NAME: str = "strategy_service"
    RETRIEVAL_SERVICE_NAME: str = "retrieval_service"
    GENERATION_SERVICE_NAME: str = "generation_service"

    # 서비스 포트 설정
    CLI_SERVICE_PORT: int = 8000
    DIALOGUE_SERVICE_PORT: int = 8001
    STRATEGY_SERVICE_PORT: int = 8002
    RETRIEVAL_SERVICE_PORT: int = 8003
    GENERATION_SERVICE_PORT: int = 8004

    # 서비스 URL들
    CLI_SERVICE_URL: str = "http://localhost:8000"
    DIALOGUE_SERVICE_URL: str = "http://localhost:8001"
    STRATEGY_SERVICE_URL: str = "http://localhost:8002"
    RETRIEVAL_SERVICE_URL: str = "http://localhost:8003"
    GENERATION_SERVICE_URL: str = "http://localhost:8004"
    
    # 로깅 설정
    
    # 원하는 형식 문자열 정의
    LOG_FORMAT : str= '%(asctime)s - %(name)s - %(levelname)s - (%(filename)s:%(lineno)d) - %(message)s'
    logger_formatter: ClassVar[logging.Formatter] = logging.Formatter(LOG_FORMAT)
    
    # 콘솔 핸들러 생성
    console_handler: ClassVar[logging.StreamHandler] = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR) 
    console_handler.setFormatter(logger_formatter)

    # 7. 파일 핸들러 생성
    file_handler: ClassVar[logging.FileHandler] = logging.FileHandler(os.getenv("LOGFILE_PATH", "service.log"))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logger_formatter)

    """
    logger 설정 예시
    self.logger = logging.getLogger(__name__)
    self.logger.setLevel(logging.DEBUG)
    self.logger.addHandler(settings.console_handler)
    self.logger.addHandler(settings.file_handler)
    """
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# 전역 설정 인스턴스
settings = Settings()

@lru_cache
def get_settings() -> Settings:
    """
    .env 파일을 읽어 Settings 객체를 생성하고 캐시합니다.
    앱 전체에서 이 함수를 호출해도 .env 파일은 딱 한 번만 읽습니다.
    """
    return Settings()