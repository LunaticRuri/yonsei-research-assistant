import requests
import pandas as pd
import json
import os
import time
from tqdm import tqdm

# ======================================================
# ⚙️ 실험 설정
# ======================================================
SERVER_URL = "http://localhost:8000/api/v1/strategy/keywords"
BENCHMARK_FILE = "benchmark_set_20.json"
OUTPUT_FILE = "ab_test_final_report.csv"

# 테스트할 5개 모델
MODELS_TO_TEST = ["openai", "gemini", "upstage", "cohere", "lora"]

# ======================================================
# 📥 데이터 준비
# ======================================================
if not os.path.exists(BENCHMARK_FILE):
    try:
        url = "https://raw.githubusercontent.com/LunaticRuri/yonsei-research-assistant/main/benchmark_set_20.json"
        r = requests.get(url)
        if r.status_code == 200:
            with open(BENCHMARK_FILE, 'wb') as f:
                f.write(r.content)
    except:
        pass

if os.path.exists(BENCHMARK_FILE):
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
else:
    print("⚠️ 벤치마크 파일을 찾을 수 없습니다.")
    questions = []

print(f"🚀 테스트 시작 (총 {len(questions)}개 문항)")
print(f"🎯 타겟 서버: {SERVER_URL}")

# ======================================================
# 🔄 테스트 루프
# ======================================================
results = []

for idx, item in enumerate(tqdm(questions)):
    query = item.get('question', item.get('query'))
    ground_truth = str(item.get('keyphrases', []))
    
    row = {
        "ID": idx + 1,
        "Question": query,
        "Ground_Truth": ground_truth
    }
    
    for model_name in MODELS_TO_TEST:
        try:
            res = requests.post(SERVER_URL, json={"query": query, "mode": model_name}, timeout=30)
            
            if res.status_code == 200:
                data = res.json()
                strat = data.get('strategy_result', {})
                retrieval = data.get('retrieval_result', {})
                
                k = strat.get('keywords', '')
                t = strat.get('latency_ms', 0)
                docs = retrieval.get('documents', [])
                d = len(docs) if isinstance(docs, list) else 0
            else:
                k, t, d = f"HTTP {res.status_code}", 0, 0
        except Exception as e:
            k, t, d = "Conn Error", 0, 0
            
        row[f"{model_name}_Keywords"] = k
        row[f"{model_name}_Latency"] = t
        row[f"{model_name}_Docs"] = d
        row[f"{model_name}_Len"] = len(str(k))
        
        time.sleep(0.1)

    results.append(row)

# ======================================================
# 💾 저장 및 통계 출력 (Update!)
# ======================================================
df = pd.DataFrame(results)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n" + "="*50)
print(f"✅ 테스트 완료! 결과 파일: {OUTPUT_FILE}")
print("📊 [모델별 성능 요약]")

for model_name in MODELS_TO_TEST:
    lat_col = f"{model_name}_Latency"
    doc_col = f"{model_name}_Docs"
    
    if lat_col in df.columns and doc_col in df.columns:
        # 평균 속도 (에러 제외)
        valid_runs = df[df[lat_col] > 0]
        avg_time = valid_runs[lat_col].mean() if not valid_runs.empty else 0
        
        # 검색 실패율 (문서 0건)
        total_runs = len(df)
        failed_runs = len(df[df[doc_col] == 0])
        fail_rate = (failed_runs / total_runs) * 100
        
        print(f"📌 [{model_name}]")
        print(f"   - 평균 속도: {avg_time:.2f} ms")
        print(f"   - 검색 실패율: {fail_rate:.1f}% ({failed_runs}/{total_runs}건)")
        print("-" * 30)

print("="*50)
