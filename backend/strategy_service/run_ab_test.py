
import requests
import pandas as pd
import json
import os
import time
from tqdm import tqdm

# ======================================================
# ⚙️ 설정 (Settings)
# ======================================================
# Strategy Service API 주소
SERVER_URL = "http://localhost:8000/api/v1/strategy/keywords"
BENCHMARK_FILE = "benchmark_set_20.json"
OUTPUT_FILE = "ab_test_final_report.csv"

# ======================================================
# 📥 데이터 로드
# ======================================================
# 벤치마크 파일이 없으면 GitHub에서 원본 다운로드
if not os.path.exists(BENCHMARK_FILE):
    print("⬇️ 벤치마크 데이터셋 다운로드 중...")
    url = "https://raw.githubusercontent.com/LunaticRuri/yonsei-research-assistant/main/benchmark_set_20.json"
    try:
        r = requests.get(url)
        r.raise_for_status()
        with open(BENCHMARK_FILE, 'wb') as f:
            f.write(r.content)
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        # 파일이 없으면 더미 데이터로 테스트 진행
        with open(BENCHMARK_FILE, 'w', encoding='utf-8') as f:
            json.dump([{"question": "디지털 리터러시가 노인에게 미치는 영향"}], f)

with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

print(f"🚀 A/B 테스트 시작 (총 {len(questions)}개 문항)")
print(f"🎯 타겟 서버: {SERVER_URL}\n")

# ======================================================
# 🧪 실험 루프 (Experiment Loop)
# ======================================================
results = []

for idx, item in enumerate(tqdm(questions)):
    # 데이터셋마다 필드명이 다를 수 있어 처리 (question or query)
    query = item.get('question', item.get('query'))
    
    # [Model A] API (OpenAI)
    try:
        res_a = requests.post(SERVER_URL, json={"query": query, "mode": "openai"}).json()
        k_a = res_a.get('strategy_result', {}).get('keywords', 'Error')
        t_a = res_a.get('strategy_result', {}).get('latency_ms', 0)
    except Exception as e: 
        k_a, t_a = f"Connection Error: {e}", 0

    # [Model B] LoRA (Local)
    try:
        res_b = requests.post(SERVER_URL, json={"query": query, "mode": "lora"}).json()
        k_b = res_b.get('strategy_result', {}).get('keywords', 'Error')
        t_b = res_b.get('strategy_result', {}).get('latency_ms', 0)
    except Exception as e: 
        k_b, t_b = f"Connection Error: {e}", 0

    results.append({
        "ID": idx + 1,
        "Question": query,
        "Model_A_Keywords": k_a,
        "Model_A_Latency(ms)": t_a,
        "Model_B_Keywords": k_b,
        "Model_B_Latency(ms)": t_b,
        # 0ms가 아니고, B가 A보다 빠르면 B 승리
        "Faster_Model": "LoRA" if (t_b < t_a and t_b > 0) else "API"
    })
    
    # 서버 과부하 방지 
    time.sleep(0.1)

# ======================================================
# 💾 결과 저장
# ======================================================
df = pd.DataFrame(results)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n" + "="*50)
print(f"✅ 테스트 완료! 결과 파일: {OUTPUT_FILE}")
if not df.empty:
    print(f"📊 평균 속도 - API: {df['Model_A_Latency(ms)'].mean():.1f}ms / LoRA: {df['Model_B_Latency(ms)'].mean():.1f}ms")
print("="*50)
