
import requests
import pandas as pd
import json
import os
import time
from tqdm import tqdm

# 설정
SERVER_URL = "http://localhost:8000/api/v1/strategy/keywords"
BENCHMARK_FILE = "benchmark_set_20.json"
OUTPUT_FILE = "ab_test_final_report.csv"

# 비교 대상 모델 (여기서 수정 가능)
MODEL_A_MODE = "openai"
MODEL_B_MODE = "lora"

# 데이터셋 준비
if not os.path.exists(BENCHMARK_FILE):
    print("⬇️ 벤치마크 데이터셋 다운로드 중...")
    try:
        url = "https://raw.githubusercontent.com/LunaticRuri/yonsei-research-assistant/main/benchmark_set_20.json"
        r = requests.get(url)
        with open(BENCHMARK_FILE, 'wb') as f:
            f.write(r.content)
    except:
        with open(BENCHMARK_FILE, 'w', encoding='utf-8') as f:
            json.dump([{"question": "테스트 질문"}], f)

with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

print(f"🚀 A/B 테스트 시작 ({MODEL_A_MODE} vs {MODEL_B_MODE})")

results = []
def test_model(query, mode):
    try:
        res = requests.post(SERVER_URL, json={"query": query, "mode": mode}, timeout=30).json()
        k = res['strategy_result']['keywords']
        t = res['strategy_result']['latency_ms']
        # 검색 결과 개수 확인 (통합 테스트용)
        d = len(res.get('retrieval_result', {}).get('documents', []))
        return k, t, d
    except: return "Error", 0, 0

for idx, item in enumerate(tqdm(questions)):
    query = item.get('question', item.get('query'))
    k_a, t_a, d_a = test_model(query, MODEL_A_MODE)
    k_b, t_b, d_b = test_model(query, MODEL_B_MODE)

    results.append({
        "ID": idx + 1, "Question": query,
        f"{MODEL_A_MODE}_Keywords": k_a, f"{MODEL_A_MODE}_Latency": t_a, f"{MODEL_A_MODE}_Docs": d_a,
        f"{MODEL_B_MODE}_Keywords": k_b, f"{MODEL_B_MODE}_Latency": t_b, f"{MODEL_B_MODE}_Docs": d_b,
        "Faster": MODEL_B_MODE if (t_b < t_a and t_b > 0) else MODEL_A_MODE
    })
    time.sleep(0.1)

df = pd.DataFrame(results)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
print(f"✅ 테스트 완료! 결과: {OUTPUT_FILE}")
