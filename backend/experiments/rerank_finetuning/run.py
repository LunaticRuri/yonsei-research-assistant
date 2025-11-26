import os
import json
import torch
import pandas as pd
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    Trainer, 
    TrainingArguments,
    DataCollatorWithPadding
)
from sklearn.model_selection import train_test_split

# ==========================================
# 1. 설정 (Configuration)
# ==========================================
MODEL_NAME = "BAAI/bge-reranker-v2-m3"
DATA_PATH = "filtered_dataset.jsonl" # 이전 단계에서 만든 데이터셋
OUTPUT_DIR = "./checkpoints"
MAX_LENGTH = 512
BATCH_SIZE = 16 # GPU 메모리에 따라 조절
NUM_EPOCHS = 1
LEARNING_RATE = 2e-5
SAVE_STEPS = 2000 # 2000 스텝마다 저장

# ==========================================
# 2. 체크포인트 감지
# ==========================================
def get_last_checkpoint(output_dir):
    if os.path.exists(output_dir):
        # checkpoint-1000, checkpoint-2000 등의 폴더 검색
        checkpoints = [d for d in os.listdir(output_dir) if d.startswith("checkpoint-")]
        if checkpoints:
            # 숫자 기준으로 정렬하여 가장 최신 체크포인트 선택
            checkpoints.sort(key=lambda x: int(x.split("-")[1]))
            last_checkpoint = os.path.join(output_dir, checkpoints[-1])
            print(f"🔄 기존 체크포인트 발견: {last_checkpoint} 에서 학습을 재개합니다.")
            return last_checkpoint
    print("🚀 새로운 학습을 시작합니다.")
    return None

last_checkpoint = get_last_checkpoint(OUTPUT_DIR)

# ==========================================
# 3. 데이터 로드 및 전처리 (Pointwise 변환)
# ==========================================
# HF Trainer는 기본적으로 (Input, Label) 쌍을 선호하므로 
# Triplet(Q, P, N)을 -> (Q, P, 1) 과 (Q, N, 0) 두 개의 데이터로 쪼갠다.

print("데이터 로드 및 전처리 중...")
data_entries = []
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        entry = json.loads(line)
        # Positive Sample (Label 1.0)
        data_entries.append({
            "text_a": entry['query'],
            "text_b": entry['positive'],
            "labels": 1.0
        })
        # Negative Sample (Label 0.0)
        data_entries.append({
            "text_a": entry['query'],
            "text_b": entry['negative'],
            "labels": 0.0
        })

df = pd.DataFrame(data_entries)
train_df, val_df = train_test_split(df, test_size=0.05, random_state=42)

# PyTorch Dataset 클래스 정의
class RerankDataset(Dataset):
    def __init__(self, data, tokenizer, max_length=512):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data.iloc[idx]
        # Cross-Encoder 입력 형식: [CLS] Query [SEP] Document [SEP]
        tokenized = self.tokenizer(
            item['text_a'],
            item['text_b'],
            truncation=True,
            max_length=self.max_length,
            padding=False # DataCollator가 배치 단위로 패딩함 (속도 향상)
        )
        tokenized['labels'] = torch.tensor(item['labels'], dtype=torch.float)
        return tokenized

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
train_dataset = RerankDataset(train_df, tokenizer, MAX_LENGTH)
eval_dataset = RerankDataset(val_df, tokenizer, MAX_LENGTH)

# ==========================================
# 4. 모델 및 트레이너 설정
# ==========================================
# num_labels=1 설정: 회귀(Regression) 모드로 동작하여 점수(Score)를 예측
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME, 
    num_labels=1,
    ignore_mismatched_sizes=True 
)

# Spot Instance에 최적화된 Training Arguments
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    overwrite_output_dir=False,      # 덮어쓰기 금지 (체크포인트 보호)
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    
    # [Spot Instance 핵심 설정]
    save_strategy="steps",           # 스텝 단위로 저장
    save_steps=SAVE_STEPS,           # 저장 간격
    save_total_limit=3,              # 디스크 용량 관리를 위해 최근 3개만 유지
    load_best_model_at_end=True,     # 학습 종료 시 가장 좋은 모델 로드
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    
    eval_strategy="steps",
    eval_steps=SAVE_STEPS,           # 저장할 때 평가도 같이 수행
    fp16=True,                       # GPU 메모리 절약 및 속도 향상
    dataloader_num_workers=4,        # 데이터 로딩 속도 향상
    report_to="none"                 # 로깅 서비스 비활성화
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer,
    data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
)

# ==========================================
# 5. 학습 실행 (Resume 로직 포함)
# ==========================================
print("학습 시작...")

# 체크포인트가 있으면 거기서부터, 없으면 처음부터(resume_from_checkpoint=None)
trainer.train(resume_from_checkpoint=last_checkpoint)

print("학습 완료. 최종 모델 저장 중...")
final_save_path = os.path.join(OUTPUT_DIR, "final_model")
trainer.save_model(final_save_path)
tokenizer.save_pretrained(final_save_path)
print(f"🎉 모든 작업이 완료되었습니다. 모델 경로: {final_save_path}")
