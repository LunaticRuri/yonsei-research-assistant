# Retrieval 부분 정량적 평가 계획

## 1. Retrieval & Rerank 단계 (검색 품질 평가)

이 부분은 비교적 명확한 정량 지표가 존재합니다. 핵심은 "Golden Dataset(질문-정답 문서 쌍)"을 얼마나 잘 만드느냐입니다.

* **평가 대상:**
  * Indexing 방식 비교 (orig vs 200 vs 200_50)
  * Rerank 모델 비교 (Base vs Fine-tuned)
* **추천 정량 지표:**
  * **Hit Rate (Recall@K):** 상위 K개 문서 내에 정답 문서가 포함되어 있는 비율. (K=1, 3, 5, 10 등으로 설정)
  * **MRR (Mean Reciprocal Rank):** 정답 문서가 몇 번째 순위에 등장하는지 역수로 계산 (1위면 1.0, 2위면 0.5...). Rerank 성능 평가에 중요합니다.
  * **NDCG@K:** 순위의 가중치를 고려하여, 정답 문서가 상위에 있을수록 더 높은 점수를 부여.

> **💡 Tip:** 문헌정보학 등 특정 분야 답안을 만드실 때, LLM에게 **(Context, Question, Ground_Truth_Doc_ID)** 쌍을 생성하게 하여, 검색된 문서 ID가 Ground Truth ID와 일치하는지 자동으로 채점하는 스크립트를 짜시면 됩니다.

-----

### 2. CRAG (Corrective RAG) 평가

CRAG의 핵심은 **"검색된 문서의 품질을 평가하고(Evaluator), 그에 따라 행동(Correct/Web Search)을 취하는가?"**입니다. 이를 정량화하려면 **Evaluator의 정확도**를 측정해야 합니다.

* **비교 대상:** CRAG 적용(O) vs 미적용(X)
* **추천 정량 지표:**
  * **Retrieval Evaluator Accuracy (분류 정확도):**
    * 데이터셋을 `[관련 있음(Correct)]`, `[모호함(Ambiguous)]`, `[관련 없음(Incorrect)]` 세 가지 케이스로 미리 라벨링합니다.
    * CRAG 내부의 Evaluator가 이 라벨을 얼마나 정확하게 맞추는지 **Accuracy, F1-Score**로 측정합니다.
  * **Trigger Rate Distribution:**
    * 전체 쿼리 중 검색(Correct)을 신뢰한 비율, 지식 정제(Ambiguous)를 수행한 비율, 웹 검색(Incorrect)으로 넘어간 비율을 수치화하여 모델의 행동 패턴을 분석합니다.
  * **End-to-End 성능 변화:**
    * CRAG 적용 시 최종 답변의 **Factual Correctness(사실 정확성)**가 얼마나 상승했는지 측정 (아래 Generation 평가 참조).

-----

### 3. Self-RAG 평가 (Generation & Reflection)

Self-RAG는 모델이 스스로 생성한 문장을 비평(Reflection)합니다. 단순 답변 비교는 어려우므로, **"LLM-as-a-Judge" (LLM을 심판으로 사용)** 방식을 사용하여 정량화해야 합니다.

* **비교 대상:** Self-RAG 적용(O) vs 미적용(X)
* **추천 정량 프레임워크: RAGAS (Retrieval Augmented Generation Assessment)**
  * RAGAS는 LLM을 사용하여 생성된 답변을 정량적인 점수(0.0 \~ 1.0)로 매기는 오픈소스 프레임워크입니다.
  * **주요 지표:**
        1. **Faithfulness (충실성):** 생성된 답변이 검색된 문서(Context)에 기반하고 있는가? (Self-RAG가 환각을 얼마나 줄였는지 측정)
        2. **Answer Relevancy (답변 관련성):** 답변이 질문에 대해 핵심을 찌르고 있는가?
        3. **Context Precision:** 검색된 내용 중 실제 정답에 기여한 비율.
* **Self-RAG 특화 지표 (Reflection Token 분석):**
  * **Critique Score Average:** Self-RAG가 생성하는 토큰(`[IsREL]`, `[IsSUP]`, `[IsUSE]`)들의 평균 점수 분포를 확인합니다. 고품질 답변일수록 `[IsSUP]`(지지됨) 비율이 높아야 합니다.

-----

### 4. 종합 요약: 단계별 검증 매트릭스 제안

작성하신 계획에 맞춰 검증 테이블을 구성하면 다음과 같습니다.

| 단계 | 비교 실험 (A/B Test) | 정량 평가 지표 (Metric) | 데이터 준비물 |
| :--- | :--- | :--- | :--- |
| **Retrieval** | Chunking (Orig / 200 / 200_50) | **Recall@5, Recall@10** (재현율 위주) | 질문 - 정답 문서 ID 쌍 |
| **Rerank** | Base vs Fine-tuned (1차/2차/정제) | **NDCG@5, MRR@10** (순위 정확도 위주) | 질문 - 정답 문서 ID 쌍 |
| **CRAG** | CRAG On/Off | **Evaluator F1-Score** (판단 정확도) **RAGAS Faithfulness** (최종 답변의 사실성) | 질문 - 문서 - 문서의 적절성 라벨(O/X) |
| **Self-RAG** | Self-RAG On/Off | **RAGAS Answer Relevance** **Win-Rate** (GPT-4에게 두 답변 중 승자를 고르게 함) | 질문 - 최종 답변 쌍 |

-----

### 5. 지금 바로 수행 가능한 Action Plan

1. **Golden Dataset 구축이 최우선:**
      * "문헌정보학" 등 특정 분야 문서를 가지고, GPT-4 등을 이용해 **[질문, 정답(Ground Truth), 참조한 문서 ID]** 쌍을 50~100개 정도 만듭니다. (이것만 있으면 Retrieval/Rerank 정량 평가는 끝납니다.)
2. **RAGAS 도입:**
      * CRAG와 Self-RAG의 "정량적 비교가 막막하다"는 점은 RAGAS 같은 자동 평가 툴을 쓰면 해결됩니다. "점수"가 나오기 때문입니다.
3. **A/B 테스트용 JSON 구조화:**
      * `generated_search_requests.json` 외에 `evaluation_results.json`을 만들어 각 실험(Chunking별, 모델별)의 점수를 기록해두세요.
