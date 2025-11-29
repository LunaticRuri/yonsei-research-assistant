import requests
import pandas as pd
import json
import os
import time
from tqdm import tqdm

# ======================================================
# ⚙️ 실험 설정 (원하는 모델을 리스트에 추가하세요!)
# ======================================================
SERVER_URL = "http://localhost:8000/api/v1/strategy/keywords"
BENCHMARK_FILE = "benchmark_set_20.json"
OUTPUT_FILE = "multi_model_comparison_report.csv"

# [중요] backend/strategy_service/core/generator.py 에 등록된 이름이어야 합니다.
MODELS_TO_TEST = ["openai", "gemini", "upstage", "lora"] 

# ======================================================
# 📥 데이터 준비
# ======================================================
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

print(f"🚀 다중 모델 비교 테스트 시작 (총 {len(questions)}개 문항)")
print(f"🥊 출전 선수: {MODELS_TO_TEST}")
print(f"🎯 타겟 서버: {SERVER_URL}\n")

# ======================================================
# 🧪 실험 함수 정의
# ======================================================
def test_model_request(query, mode):
    try:
        # 타임아웃을 넉넉히 (API 모델들이 느릴 수 있음)
        response = requests.post(SERVER_URL, json={"query": query, "mode": mode}, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            strat = data.get('strategy_result', {})
            keywords = strat.get('keywords', '')
            latency = strat.get('latency_ms', 0)
            
            # 검색 결과 개수 확인
            retrieval = data.get('retrieval_result', {})
            docs = retrieval.get('documents', [])
            doc_count = len(docs) if isinstance(docs, list) else 0
            
            return keywords, latency, doc_count
        else:
            return f"HTTP Error {response.status_code}", 0, 0
    except Exception as e:
        return f"Conn Error", 0, 0

# ======================================================
# 🔄 실험 루프 실행
# ======================================================
results = []

for idx, item in enumerate(tqdm(questions)):
    query = item.get('question', item.get('query'))
    
    # 1. 결과 행 초기화
    row = {
        "ID": idx + 1,
        "Question": query
    }
    
    fastest_time = float('inf')
    fastest_model = "None"

    # 2. 각 모델별 테스트 반복 수행
    for model_name in MODELS_TO_TEST:
        k, t, d = test_model_request(query, model_name)
        
        # 결과 기록
        row[f"{model_name}_Keywords"] = k
        row[f"{model_name}_Latency(ms)"] = t
        row[f"{model_name}_Docs"] = d
        
        # 가장 빠른 모델 갱신 (에러(0ms) 제외)
        if t > 0 and t < fastest_time:
            fastest_time = t
            fastest_model = model_name
            
        time.sleep(0.1) # 서버 부하 방지

    # 3. 승자 기록
    row["Fastest_Model"] = fastest_model
    results.append(row)

# ======================================================
# 💾 결과 저장 및 통계
# ======================================================
df = pd.DataFrame(results)
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\\n" + "="*50)
print(f"✅ 테스트 완료! 결과 파일: {OUTPUT_FILE}")
print("📊 [모델별 성능 요약]")

for model_name in MODELS_TO_TEST:
    lat_col = f"{model_name}_Latency(ms)"
    doc_col = f"{model_name}_Docs"
    
    if lat_col in df.columns and doc_col in df.columns:
        # 1. 평균 속도 (에러 제외)
        avg_time = df[df[lat_col] > 0][lat_col].mean()
        
        # 2. 검색 실패율 (문서 개수가 0인 비율)
        total_runs = len(df)
        failed_runs = len(df[df[doc_col] == 0])
        fail_rate = (failed_runs / total_runs) * 100
        
        print(f"📌 [{model_name}]")
        print(f"   - 평균 속도: {avg_time:.2f} ms")
        print(f"   - 검색 실패율: {fail_rate:.1f}% ({failed_runs}/{total_runs}건)")
        print("-" * 30)

print("="*50)
