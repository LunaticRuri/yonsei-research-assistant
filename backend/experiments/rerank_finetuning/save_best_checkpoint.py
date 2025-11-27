import os
import json
import shutil
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# 설정 (run.py와 동일하게 맞춤)
OUTPUT_DIR = "./checkpoints"
FINAL_SAVE_PATH = os.path.join(OUTPUT_DIR, "final_model")
MODEL_NAME = "BAAI/bge-reranker-v2-m3"

def find_best_checkpoint(output_dir):
    # 1. 모든 체크포인트 폴더 검색
    if not os.path.exists(output_dir):
        print(f"❌ {output_dir} 폴더가 없습니다.")
        return None
        
    checkpoints = [d for d in os.listdir(output_dir) if d.startswith("checkpoint-")]
    if not checkpoints:
        print("❌ 체크포인트가 하나도 없습니다.")
        return None

    # 2. 가장 최신 체크포인트 찾기 (여기에 전체 학습 기록이 있음)
    checkpoints.sort(key=lambda x: int(x.split("-")[1]))
    latest_checkpoint = os.path.join(output_dir, checkpoints[-1])
    state_file = os.path.join(latest_checkpoint, "trainer_state.json")

    if not os.path.exists(state_file):
        print(f"❌ {state_file} 파일을 찾을 수 없습니다.")
        return None

    # 3. trainer_state.json 읽어서 best_model_checkpoint 확인
    with open(state_file, "r") as f:
        state = json.load(f)
    
    best_model_path = state.get("best_model_checkpoint")
    
    if best_model_path and os.path.exists(best_model_path):
        print(f"✅ 기록상 가장 성능이 좋은 모델: {best_model_path}")
        print(f"   (Best Metric: {state.get('best_metric')})")
        return best_model_path
    else:
        print("⚠️ Best model 정보를 찾을 수 없거나 경로가 유효하지 않습니다.")
        print(f"ℹ️ 대신 가장 최신 체크포인트를 사용합니다: {latest_checkpoint}")
        return latest_checkpoint

def save_final_model():
    best_ckpt = find_best_checkpoint(OUTPUT_DIR)
    
    if best_ckpt:
        print(f"💾 모델 변환 및 저장 중... ({best_ckpt} -> {FINAL_SAVE_PATH})")
        
        # 모델 로드
        model = AutoModelForSequenceClassification.from_pretrained(best_ckpt, num_labels=1)
        tokenizer = AutoTokenizer.from_pretrained(best_ckpt)
        
        # 최종 경로에 저장
        model.save_pretrained(FINAL_SAVE_PATH)
        tokenizer.save_pretrained(FINAL_SAVE_PATH)
        
        print(f"🎉 복구 완료! 최종 모델이 여기에 저장되었습니다: {FINAL_SAVE_PATH}")
    else:
        print("❌ 복구할 모델을 찾지 못했습니다.")

if __name__ == "__main__":
    save_final_model()