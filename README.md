# Yonsei Research Assistant - 수리조교

연세대학교 학술 연구 보조 AI 에이전트 '수리조교'의 마이크로서비스 아키텍처 구현

## 프로젝트 구조

```text
yonsei-research-assistant/
├── frontend/                 # SvelteKit 프론트엔드
│   ├── src/   
│   ├── static/
│   └── ...
│
└── backend/                  # 마이크로서비스들
    ├── api-gateway/          # 중앙 API Gateway (Port: 8000)
    ├── dialogue-service/     # 소크라테스식 대화 서비스 (Port: 8001)
    ├── strategy-service/     # 검색 전략 생성 서비스 (Port: 8002)
    ├── rag-service/         # RAG 분석 서비스 (Port: 8003)
    ├── search-agent-service/ # 도서관 검색 에이전트 (Port: 8004)
    ├── shared/              # 공통 모델 및 설정
    ├── docker-compose.yml   # 전체 서비스 오케스트레이션
    └── .env.example        # 환경변수 템플릿
```

## 서비스별 기능

### 1. API Gateway (Port: 8000)

- 모든 마이크로서비스 요청을 중앙에서 관리
- CORS 설정 및 인증 처리
- 서비스 간 요청 라우팅

### 2. Dialogue Service (Port: 8001)

- 소크라테스식 대화를 통한 연구 주제 구체화
- OpenAI GPT-4o를 활용한 지능형 대화
- 대화 단계별 진행 관리

### 3. Strategy Service (Port: 8002)

- 대화 내용을 바탕으로 검색 전략 생성
- 키워드 분석 및 확장
- 불리언 검색식 자동 생성

### 4. RAG Service (Port: 8003)

- ChromaDB 기반 벡터 검색
- 학술 문헌 분석 및 핵심 논쟁 지점 추출
- 문서 전처리 및 임베딩

### 5. Search Agent Service (Port: 8004)

- 연세대학교 도서관 실시간 검색
- 웹 스크래핑을 통한 소장 정보 확인
- 검색 결과 후처리 및 랭킹

## 시작하기

### 환경 설정

- 환경변수 파일 생성:

```bash
cp backend/.env.example backend/.env
```

- `.env` 파일에서 필요한 값들 설정:

```text
OPENAI_API_KEY=your_actual_api_key_here
```

### 개발 환경 실행

#### 백엔드 서비스들 개별 실행

```bash
# API Gateway
cd backend/api-gateway
pip install -r requirements.txt
python main.py

# Dialogue Service
cd backend/dialogue-service
pip install -r requirements.txt
python main.py

# Strategy Service
cd backend/strategy-service
pip install -r requirements.txt
python main.py

# RAG Service
cd backend/rag-service
pip install -r requirements.txt
python main.py

# Search Agent Service
cd backend/search-agent-service
pip install -r requirements.txt
python main.py
```

#### Docker Compose로 전체 실행

```bash
cd backend
docker-compose up --build
```

#### 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

## API 엔드포인트

### API Gateway (<http://localhost:8000>)

- `POST /api/dialogue` - 소크라테스식 대화
- `POST /api/strategy/generate` - 검색 전략 생성
- `POST /api/strategy/update` - 검색 전략 업데이트
- `POST /api/rag/analyze` - RAG 분석
- `POST /api/search/execute` - 도서관 검색 실행

## 기술 스택

### 프론트엔드

- SvelteKit
- Vite
- Axios

### 백엔드

- FastAPI
- Pydantic
- OpenAI GPT-4o
- ChromaDB
- BeautifulSoup4
- Requests

### 인프라

- Docker & Docker Compose
- Python 3.11+

## 개발 참고사항

### 공통 모델

모든 서비스에서 사용하는 Pydantic 모델들은 `backend/shared/models.py`에 정의되어 있습니다.

### 설정 관리

환경별 설정은 `backend/shared/config.py`에서 중앙 관리됩니다.

### 에러 처리

각 서비스는 표준화된 에러 응답 형식을 사용합니다.

### 로깅

모든 서비스에서 구조화된 로깅을 사용합니다.

## 주의사항

1. **웹 스크래핑**: 도서관 웹사이트 구조 변경 시 `search-agent-service`의 스크래핑 로직 수정 필요
2. **API 비용**: OpenAI API 사용량 모니터링 필요
3. **벡터 DB**: RAG 서비스 초기 실행 시 샘플 데이터 수집 필요

## 라이센스

이 프로젝트는 연세대학교 교육 목적으로 개발되었습니다.
