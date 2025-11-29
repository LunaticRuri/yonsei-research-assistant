
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

# [비교할 모델 선택] 
# backend/strategy_service/core/generator.py 에 등록된 이름이어야 합니다.
# 예: "openai", "lora", "gemini", "upstage" 등
MODEL_A_MODE = "openai"  
MODEL_B_MODE = "lora"    

# ======================================================
# 📥 데이터 준비
# ======================================================
if not os.path.exists(BENCHMARK_FILE):
    print("⬇️ 벤치마크 데이터셋 다운로드 중...")
    try:
        url = "https://raw.githubusercontent.com/LunaticRuri/yonsei-research-assistant/main/benchmark_set_20.json"
        r = requests.get(url)
        r.raise_for_status()
        with open(BENCHMARK_FILE, 'wb') as f:
            f.write(r.content)
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        # 더미 데이터 생성
        with open(BENCHMARK_FILE, 'w', encoding='utf-8') as f:
            json.dump([{"question": "테스트 질문입니다"}], f)

with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
    questions = json.load(f)

print(f"🚀 A/B 테스트 시작 (총 {len(questions)}개 문항)")
print(f"🥊 대결 구도: [{MODEL_A_MODE}] vs [{MODEL_B_MODE}]")
print(f"🎯 타겟 서버: {SERVER_URL}
")

# ======================================================
# 🧪 실험 함수 정의
# ======================================================
def test_model_request(query, mode):
    # 서버에 요청을 보내고 키워드, 속도, 검색결과 수를 반환
    try:
        response = requests.post(SERVER_URL, json={"query": query, "mode": mode}, timeout=60) # 타임아웃 넉넉히
        
        if response.status_code == 200:
            data = response.json()
            # Strategy 결과
            strat = data.get('strategy_result', {})
            keywords = strat.get('keywords', '')
            latency = strat.get('latency_ms', 0)
            
            # Retrieval 결과 (문서 개수)
            retrieval = data.get('retrieval_result', {})
            docs = retrieval.get('documents', [])
            doc_count = len(docs) if isinstance(docs, list) else 0
            
            return keywords, latency, doc_count
        else:
            return f"HTTP Error {response.status_code}", 0, 0
    except Exception as e:
        return f"Connection Error: {str(e)}", 0, 0

# ======================================================
# 🔄 실험 루프 실행
# ======================================================
results = []

for idx, item in enumerate(tqdm(questions)):
    query = item.get('question', item.get('query'))
    
    # 1. Model A 테스트
    k_a, t_a, d_a = test_model_request(query, MODEL_A_MODE)
    
    # 2. Model B 테스트
    k_b, t_b, d_b = test_model_request(query, MODEL_B_MODE)

    # 3. 결과 기록 (컬럼명에 모델 이름 포함)
    results.append({
        "ID": idx + 1,
        "Question": query,
        
        # Model A 결과
        f"{MODEL_A_MODE}_Keywords": k_a,
        f"{MODEL_A_MODE}_Latency(ms)": t_a,
        f"{MODEL_A_MODE}_Docs": d_a,
        
        # Model B 결과
        f"{MODEL_B_MODE}_Keywords": k_b,
        f"{MODEL_B_MODE}_Latency(ms)": t_b,
        f"{MODEL_B_MODE}_Docs": d_b,
        
        # 승자 판정 (속도 기준)
        "Faster_Model": MODEL_B_MODE if (t_b < t_a and t_b > 0) else (MODEL_A_MODE if t_a > 0 else "Error")
    })
    
    time.sleep(0.1) 

# ======================================================
# 💾 결과 저장 및 통계
# ======================================================
df = pd.DataFrame(results)
output_filename = f"ab_test_{MODEL_A_MODE}_vs_{MODEL_B_MODE}.csv" # 파일명도 자동 변경
df.to_csv(output_filename, index=False, encoding="utf-8-sig")

print("\n" + "="*50)
print(f"✅ 테스트 완료! 결과 파일: {output_filename}")

# 평균 속도 계산 (0인 값 제외)
mean_a = df[df[f"{MODEL_A_MODE}_Latency(ms)"] > 0][f"{MODEL_A_MODE}_Latency(ms)"].mean()
mean_b = df[df[f"{MODEL_B_MODE}_Latency(ms)"] > 0][f"{MODEL_B_MODE}_Latency(ms)"].mean()

print(f"📊 [평균 응답 속도]")
print(f"   - {MODEL_A_MODE}: {mean_a:.2f} ms")
print(f"   - {MODEL_B_MODE}: {mean_b:.2f} ms")
print("="*50)
