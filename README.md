# Yonsei Research Assistant - 수리조교

연세대학교 정보 이용자의 탐색을 지원하는 RAG 모델 개발

## 프로젝트 구조

```text
/yonsei-research-assistant
├── frontend/                 # SvelteKit 프론트엔드 (구현 X)
│   └── ...
│
└── backend/                  # 마이크로서비스 및 인프라
    ├── cli_interface/        # 1. 작동 및 시연을 위한 프로그램
    |
    ├── dialogue_service/     # 2. 사용자-AI Agent 대화 통한 질문 구체화 (Port: 8001)
    │
    ├── strategy_service/     # 3. RAG 쿼리 처리 (Port: 8002)
    │   │                     # (RAG 다이어그램의 'Query Translation', 'Query Construciton', 'Routing' 담당)
    │   └── ...
    │
    ├── retrieval_service/    # 4. 데이터 검색/융합 (Port: 8003)
    │   │                     # (RAG 다이어그램의 'Retrieval' 담당)
    │   └── ...
    │
    ├── generation_service/   # 5. RAG 답변 생성 (Port: 8004)
    │   │                     # (RAG 다이어그램의 'Generation' 담당)
    │   └── ...
    │
    ├── indexing_worker/      # 6. 데이터 색인 워커 (API 아님)
    │   │                     # (RAG 다이어그램의 'Indexing' 담당)
    │   └── ...
    │
    ├── shared/               # 공통 Pydantic 모델, 설정, 유틸
    │   ├── models.py
    │   └── config.py
    |
    └── .env                  # 환경변수
```

## 서비스별 기능

### 1. CLI Interface

- 전체적인 작동 모습과 시연을 위한 클라이언트측 프로토타입

### 2. Dialogue Service (Port: 8001)

- 소크라테스식 대화를 통한 연구 주제 구체화
- Gemini를 활용한 지능형 대화

### 3. Strategy Service (Port: 8002)

- Query Translation, Qury Construciton, Routing 단계 담당
- 키워드 분석 및 확장, 불리언 검색식 자동 생성
- Query Translation: Multi-query, Step-back, HyDE 로직을 적용하여 검색 효율이 좋은 질문들로 변환
- Routing : 질문을 분석하여 retrieval-service에게 "어떤 경로로 검색할지" 지시 (e.g., "도서" -> Vector DB, "연구 논문" -> 연세대학교 학술정보원)
- Query Construction : Text-to-SQL, Self-query 로직을 생성하여 retrieval-service에 전달

### 4. Retrieval Service (Port: 8003)

- Retrieval 단계 담당
- strategy-service의 요청에 따라 모든 데이터 소스에서 문서를 검색
- Retriever : VectorDB, SQL DB, 웹 등의 소스에서 데이터를 수집
- Ranking & Fusion : Rerank 로직을 사용해 여러 소스에서 가져온 결과를 조합하고 순위 설정
- Refinement : CRAG 로직을 이용해 검색 결과의 품질 평가

### 5. Generation Service (Port: 8004)

- Generation 단계 담당
- retrieval-service가 전달한 최종 컨텍스트를 바탕으로 LLM의 답변을 생성
- 최종 출력 이전 Active Retreival(Self-RAG)를 사용해 답변의 품질이 낮다고 생각되면, 다시 호출해 추가 검색을 요청

### 6. Indexing Worker

- Indexing 단계 담당 (API X)
- Chunk Optimization, Multi-representation 등 사용
- 수동 실행 또는 스케줄러로 주기적 실행 가정 but 지금 단계에선 구체적 구현 필요 X
