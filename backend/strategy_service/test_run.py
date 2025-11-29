
import sys
import os

# [중요] 모듈 경로 설정 (backend/strategy_service 폴더를 인식하게 함)
current_dir = os.getcwd()
sys.path.append(os.path.join(current_dir, "backend/strategy_service"))

from core.generator import QueryTranslationService

# --- 테스트 시작 ---
print("\n" + "="*50)
print("🚀 Strategy Service 모의 테스트 (Mocking Test)")
print("="*50)

# 1. 서비스 초기화 (가짜 모델 경로 입력 -> Mock 모드 자동 진입)
ADAPTER_PATH = "./models/query_translation_adapter_final"
service = QueryTranslationService(adapter_path=ADAPTER_PATH)

# 2. 테스트 질문
test_query = "디지털 리터러시가 노인 층에 미치는 영향에 대한 논문 찾아줘"
print(f"\n🔎 질문: {test_query}")

# 3. [Test A] API 모드 (API 키가 없으면 에러 메시지 반환)
print("-" * 30)
print("📡 [Mode A: API] 실행 중...")
res_api = service.generate_keywords(test_query, mode="api")
print(f"▶ 결과: {res_api['keywords']}")
print(f"▶ 시간: {res_api['latency_ms']} ms")

# 4. [Test B] LoRA 모드 (모델 없으므로 Mock 결과 반환)
print("-" * 30)
print("🏠 [Mode B: LoRA] 실행 중...")
res_lora = service.generate_keywords(test_query, mode="lora")
print(f"▶ 결과: {res_lora['keywords']}")
print(f"▶ 시간: {res_lora['latency_ms']} ms")

print("="*50 + "\n✅ 테스트 완료!")
