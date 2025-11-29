
import csv
import os
from datetime import datetime

LOG_FILE = "ab_test_log.csv"

def log_experiment(query, model_mode, keywords, latency):
    file_exists = os.path.isfile(LOG_FILE)
    
    try:
        with open(LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            # 파일이 없으면 헤더(제목) 작성
            if not file_exists:
                writer.writerow(["Timestamp", "Query", "Model", "Keywords", "Latency(ms)"])
                
            writer.writerow([
                datetime.now().isoformat(),
                query,
                model_mode,
                str(keywords),
                latency
            ])
        print("📝 [Logger] 실험 결과 기록 완료")
    except Exception as e:
        print(f"❌ [Logger] 기록 실패: {e}")
