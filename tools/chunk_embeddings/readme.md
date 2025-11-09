# Multirepresentation Indexing 실험을 위한 임베딩

**임베딩시 KURE-v1 사용!**
<https://huggingface.co/nlpai-lab/KURE-v1>
**GPU 사용해야 할 거 같음 - GCP 등 빌려서 나중에 처리**

- [ ] embeddings 에 있는 doc 부분을 200자 단위로 끊어서 다시 저장
- [ ] CPU로는 너무 느려서 GPU 인스턴스를 하나 빌려서 처리해야할 것 같음
- [ ] 1) 전체 임베딩 2) 부분 임베딩 3) 전체 + 부분 임베딩 결과 비교
- [ ] 다른 임베딩 모델이나 직접 임베딩 하는 것도 고려 가능

## 사용법

### 요구사항

```bash
pip install sentence-transformers tqdm
```

### 실행

```bash
python run.py --db-path /path/to/your/database.db
```

### 옵션

- `--db-path`: SQLite 데이터베이스 파일 경로 (필수)
- `--chunk-size`: 텍스트 청크 크기 (기본값: 200자)
- `--embedding-batch-size`: 임베딩 생성 배치 크기 (기본값: 500)
- `--save-interval`: 로그 출력 간격 (기본값: 100)

### 예시

```bash
# 기본 사용 (CPU 코어 수만큼 워커 생성)
python run.py --db-path /path/to/database.db

# 워커 수 지정
python run.py --db-path /path/to/database.db --num-workers 4

# 청크 크기와 배치 크기 조정
python run.py --db-path /path/to/database.db --chunk-size 100 --embedding-batch-size 64

# 모든 옵션 사용
python run.py \
  --db-path /path/to/database.db \
  --chunk-size 100 \
  --embedding-batch-size 32 \
  --save-interval 50 \
  --num-workers 8
```

## 특징

1. **재시작 가능**: 중간에 중단되어도 이미 처리된 ISBN은 건너뛰고 나머지만 처리
2. **배치 처리**: 효율적인 임베딩 생성을 위한 배치 처리
3. **진행 상황 표시**: tqdm을 통한 실시간 진행 상황 표시
4. **로깅**: 상세한 로그를 통한 진행 상황 추적
