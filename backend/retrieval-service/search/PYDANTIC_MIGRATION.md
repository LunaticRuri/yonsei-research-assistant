# LibraryScraper Pydantic 모델

1. **타입 안전성**
   - Enum과 Literal을 사용하여 잘못된 값 입력 방지
   - IDE 자동완성 지원으로 개발 경험 향상
2. **자동 검증**
   - Pydantic의 `field_validator`를 통한 자동 유효성 검증
   - 연도 범위, 검색어 길이, 결과 수 등 자동 검증
3. **명확한 문서화**
   - 각 필드에 상세한 설명과 예시 제공
   - 타입 힌트로 명확한 파라미터 정의

## Pydantic 모델

### SearchField (Enum)

검색 필드 타입을 정의합니다.

```python
class SearchField(str, Enum):
    TOTAL = "TOTAL"      # 전체
    TITLE = "1"          # 서명(책제목)
    AUTHOR = "2"         # 저자
    PUBLISHER = "3"      # 출판사
    SUBJECT = "4"        # 주제어
```

### MaterialType (Enum)

자료 유형을 정의합니다.

```python
class MaterialType(str, Enum):
    TOTAL = "TOTAL"                 # 전체
    BOOK = "m"                      # 단행본
    SERIAL = "s"                    # 연속간행물
    MULTIMEDIA = "b;p;v;x;u;c"      # 멀티미디어/비도서
    THESIS = "t"                    # 학위논문
    OLD_BOOK = "o"                  # 고서
    ARTICLE = "zart"                # 기사
```

### QueryOperator (Enum)

검색 연산자를 정의합니다.

```python
class QueryOperator(str, Enum):
    AND = "and"
    OR = "or"
    NOT = "not"
```

### AdditionalQuery (BaseModel)

추가 검색 조건을 정의합니다.

```python
class AdditionalQuery(BaseModel):
    search_field: SearchField = Field(default=SearchField.TOTAL)
    query: str = Field(..., min_length=1)
    operator: QueryOperator = Field(default=QueryOperator.AND)
```

### YearRange (BaseModel)

발행 연도 범위를 정의하며, 자동으로 유효성을 검증합니다.

```python
class YearRange(BaseModel):
    from_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    to_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    
    # 종료 연도 >= 시작 연도 자동 검증
```

### LibraryHoldingsSearchParams (BaseModel)

모든 검색 파라미터를 하나의 구조화된 모델로 정의합니다.

```python
class LibraryHoldingsSearchParams(BaseModel):
    query: str
    search_field: SearchField = SearchField.TOTAL
    additional_queries: List[AdditionalQuery] = []
    material_types: List[MaterialType] = [MaterialType.TOTAL]
    year_range: Optional[YearRange] = None
    results_per_page: Literal[5, 10, 15, 20, 30, 50, 100] = 10
```

## 사용 예시

### 예시 1: 간단한 검색

```python
from library_holdings_scraper import LibraryHoldingsScraper, LibraryHoldingsSearchParams

scraper = LibraryHoldingsScraper()

params = LibraryHoldingsSearchParams(
    query="인공지능",
    results_per_page=20
)

results = await scraper.execute_holdings_search(params, max_results=10)
```

### 예시 2: 고급 검색 (OR/NOT 연산자)

```python
from library_holdings_scraper import (
    LibraryHoldingsSearchParams,
    AdditionalQuery,
    QueryOperator,
    YearRange
)

params = LibraryHoldingsSearchParams(
    query="휴대폰",
    additional_queries=[
        AdditionalQuery(query="스마트폰", operator=QueryOperator.OR),
        AdditionalQuery(query="아이폰", operator=QueryOperator.NOT)
    ],
    year_range=YearRange(from_year=2020, to_year=2025),
    results_per_page=50
)

results = await scraper.execute_holdings_search(params)
```

### 예시 3: 필드별 검색

```python
from library_holdings_scraper import SearchField

params = LibraryHoldingsSearchParams(
    query="머신러닝",
    search_field=SearchField.TITLE,  # 서명으로 검색
    additional_queries=[
        AdditionalQuery(
            search_field=SearchField.AUTHOR,
            query="김철수",
            operator=QueryOperator.AND
        ),
        AdditionalQuery(
            search_field=SearchField.SUBJECT,
            query="딥러닝",
            operator=QueryOperator.AND
        )
    ],
    results_per_page=100
)

results = await scraper.execute_holdings_search(params)
```

### 예시 4: 자료 유형 필터링

```python
from library_holdings_scraper import MaterialType

params = LibraryHoldingsSearchParams(
    query="기후변화",
    material_types=[
        MaterialType.SERIAL,   # 연속간행물
        MaterialType.THESIS    # 학위논문
    ],
    year_range=YearRange(from_year=2020),
    results_per_page=30
)

results = await scraper.execute_holdings_search(params)
```

## 자동 검증

Pydantic은 다음을 자동으로 검증합니다:

### 1. 연도 범위 검증

```python
# ❌ 오류: 종료 연도가 시작 연도보다 작음
params = LibraryHoldingsSearchParams(
    query="테스트",
    year_range=YearRange(from_year=2025, to_year=2020)
)
# ValueError: 종료 연도는 시작 연도보다 크거나 같아야 합니다
```

### 2. 검색어 길이 검증

```python
# ❌ 오류: 빈 검색어
params = LibraryHoldingsSearchParams(query="")
# ValidationError: String should have at least 1 character
```

### 3. 페이지당 결과 수 검증

```python
# ❌ 오류: 허용되지 않는 값
params = LibraryHoldingsSearchParams(
    query="테스트",
    results_per_page=25  # 5, 10, 15, 20, 30, 50, 100만 허용
)
# ValidationError: Input should be 5, 10, 15, 20, 30, 50 or 100
```

### 4. Enum 값 검증

```python
# ❌ 오류: 잘못된 Enum 값
params = LibraryHoldingsSearchParams(
    query="테스트",
    search_field="invalid_field"
)
# ValidationError: Invalid enum value
```

## 새로운 코드

```python
params = LibraryHoldingsSearchParams(
    query="인공지능",
    search_field=SearchField.TITLE,
    additional_queries=[
        AdditionalQuery(
            search_field=SearchField.AUTHOR,
            query="김철수",
            operator=QueryOperator.AND
        ),
        AdditionalQuery(
            search_field=SearchField.SUBJECT,
            query="머신러닝",
            operator=QueryOperator.AND
        )
    ],
    material_types=[MaterialType.BOOK, MaterialType.SERIAL],
    year_range=YearRange(from_year=2020, to_year=2025),
    results_per_page=50
)

results = await scraper.execute_holdings_search(params)
```

## 테스트

예시 파일을 실행하여 Pydantic 모델을 테스트할 수 있습니다:

```bash
cd backend/retrieval-service/search
python3 example_usage.py
```
