# 파일명: run_poc_test.py
# (backend/strategy-service 폴더에 저장)

import os
import time
import openai
import anthropic
from dotenv import load_dotenv

# --- 1. 환경 설정 ---
print("INFO: .env 파일에서 API 키를 로드합니다...")
load_dotenv()

try:
    openai_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print("INFO: API 클라이언트 초기화 완료.")
except KeyError:
    print("오류: .env 파일에 OPENAI_API_KEY 또는 ANTHROPIC_API_KEY가 없습니다.")
    exit()

# --- 2. v8.0 기획안 핵심 요소 정의 ---

# 2-1. 테스트 데이터셋 (v8.0 기획안의 '수제 불리언 문제' 예시)
# OO님이 이 부분을 자유롭게 바꿔가며 테스트해 보세요.
SCENARIO = "김영희 저자의 2023년 이후 'AI' 논문, 단 한국어 논문은 제외"
GROUND_TRUTH = '(Author = "김영희") AND (PublicationYear >= 2023) AND (Keyword = "AI") AND (NOT Language = "Korean")'

# 2-2. 프롬프트 (v8.0 기획안의 Prompt A, C)
PROMPT_A_TEMPLATE = """
너는 연세대 도서관 사서야. 다음 시나리오를 불리언 쿼리로 바꿔줘:
{scenario}
"""

PROMPT_C_TEMPLATE = """
너는 연세대 도서관 검색 전문가다.
사용 가능한 필드는 [Author, Keyword, PublicationYear, Language] 뿐이다.
이 스키마를 엄격히 준수하여 다음 시나리오를 불리언 쿼리로 바꿔줘:
{scenario}
"""

# --- 3. 모델 호출 함수 정의 ---

def get_gpt4o_response(prompt):
    """Tier 1: GPT-4o 호출"""
    start_time = time.time()
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        text = response.choices[0].message.content
        latency = time.time() - start_time
        return text, f"{latency:.2f}초"
    except Exception as e:
        return f"GPT-4o 오류: {e}", "N/A"

def get_haiku_response(prompt):
    """Tier 2: Claude 3 Haiku 호출"""
    start_time = time.time()
    try:
        response = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        text = response.content[0].text
        latency = time.time() - start_time
        return text, f"{latency:.2f}초"
    except Exception as e:
        return f"Haiku 오류: {e}", "N/A"

# --- 4. PoC 테스트 실행 및 결과 출력 ---

def run_poc():
    print("=" * 50)
    print("🚀 v8.0 기획안 PoC 테스트를 시작합니다.")
    print(f"테스트 시나리오: {SCENARIO}")
    print(f"   (정답 쿼리): {GROUND_TRUTH}")
    print("=" * 50 + "\n")

    # 2x2 매트릭스 테스트
    tests_to_run = [
        ("GPT-4o (Tier 1)", "A (Zero-Shot)", PROMPT_A_TEMPLATE.format(scenario=SCENARIO), get_gpt4o_response),
        ("GPT-4o (Tier 1)", "C (Schema)", PROMPT_C_TEMPLATE.format(scenario=SCENARIO), get_gpt4o_response),
        ("Haiku (Tier 2)", "A (Zero-Shot)", PROMPT_A_TEMPLATE.format(scenario=SCENARIO), get_haiku_response),
        ("Haiku (Tier 2)", "C (Schema)", PROMPT_C_TEMPLATE.format(scenario=SCENARIO), get_haiku_response),
    ]

    results_for_demo = []

    for model_name, prompt_name, final_prompt, model_function in tests_to_run:
        print(f"--- [실행 중: {model_name} + {prompt_name}] ---")
        response, latency = model_function(final_prompt)
        
        print(f"응답 속도: {latency}")
        print(f"모델 응답:\n{response}\n")
        
        # 시연용 데이터 수집
        results_for_demo.append((model_name, prompt_name, response, latency))

    return results_for_demo

if __name__ == "__main__":
    run_poc()