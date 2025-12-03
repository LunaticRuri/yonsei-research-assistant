#**********************************************
# DEPRICIATED!
#**********************************************
# backend/strategy-service/config.py (최종 수정본)

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# 이 config.py 파일의 위치(strategy-service)를 기준으로 
# .env 파일의 경로를 계산합니다.
env_path = Path(__file__).parent.parent / '.env'

class Settings(BaseSettings):
    """
    서비스의 환경 변수를 관리하는 설정 클래스입니다.
    .env 파일에서 값을 읽어옵니다.
    """

    model_config = SettingsConfigDict(
        env_file=env_path,  # backend/.env 파일을 읽도록 경로 설정
        env_file_encoding='utf-8',
        extra='ignore' # .env에 정의된 다른 변수들은 무시
    )

    # .env 파일에서 읽어올 변수들을 타입과 함께 정의합니다.
    STRATEGY_LLM_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str

    # --- [여기 추가!] Redis 설정 ---
    # .env에 값이 없으면 'redis'를 기본값으로 사용
    REDIS_HOST: str = "redis" 
    # .env에 값이 없으면 6379를 기본값으로 사용
    REDIS_PORT: int = 6379
    # -----------------------------

# 설정 객체를 인스턴스화하여 다른 파일에서 임포트해 쓸 수 있게 합니다.
settings = Settings()

# --- [수정] 프롬프트 관련 정의를 settings 객체 뒤로 이동 ---

# 1. 프롬프트 폴더 경로 정의
PROMPT_DIR = Path(__file__).parent / "prompts"

# 2. 함수 정의 (★먼저★)
def load_prompt(filename: str) -> str:
    """
    prompts 폴더에서 파일 이름을 받아 
    내용(프롬프트 텍스트)을 문자열로 반환합니다.
    """
    prompt_path = PROMPT_DIR / filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"경고: 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
        return f"Error: Prompt file '{filename}' not found."
    except Exception as e:
        print(f"경고: 프롬프트 파일 읽기 오류 '{filename}': {e}")
        return f"Error reading prompt file: {e}"

# 3. 함수 사용 (★나중에★)
PROMPT_GEN_SYNONYMS = load_prompt("generate_synonyms.txt")
PROMPT_GEN_RELATED = load_prompt("generate_related_terms.txt")
PROMPT_ID_ACADEMIC = load_prompt("identify_academic_fields.txt")


# (선택적) 잘 로드되었는지 테스트 (파일의 맨 마지막에 위치)
if __name__ == "__main__":
    print("로드된 설정:")
    print(f"Strategy Model: {settings.STRATEGY_LLM_MODEL}")
    print(f"OpenAI Key (일부): ...{settings.OPENAI_API_KEY[-4:]}")
    print("\n프롬프트 로드 테스트:")
    print(f"  - Synonyms Prompt (첫 30자): {PROMPT_GEN_SYNONYMS[:30]}...")