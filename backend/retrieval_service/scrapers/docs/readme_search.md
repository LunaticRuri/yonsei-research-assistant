# Library Scraper Pydantic 모델

연세대학교 도서관 스크래퍼는 두 가지 타입을 제공합니다:

- **LibraryHoldingsScraper**: 소장자료 검색 (단행본, 학위논문 등)
- **ElectronicResourceScraper**: 전자자료 검색 (학술논문, E-Journal 등)

## 주요 특징

1. **타입 안전성**
   - Enum과 Literal을 사용하여 잘못된 값 입력 방지
   - IDE 자동완성 지원으로 개발 경험 향상
2. **자동 검증**
   - Pydantic의 `field_validator`를 통한 자동 유효성 검증
   - 연도 범위, 검색어 길이, 결과 수 등 자동 검증
3. **명확한 문서화**
   - 각 필드에 상세한 설명과 예시 제공
   - 타입 힌트로 명확한 파라미터 정의
4. **자동 로그인/로그아웃**
   - `async with` 패턴으로 세션 관리 자동화
   - 환경변수 기반 안전한 인증

---

# 1. LibraryHoldingsScraper (소장자료)

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

## 소장자료 사용 예시

### 예시 1: 간단한 검색

```python
from library_holdings_scraper import LibraryHoldingsScraper, LibraryHoldingsSearchParams

# async with 패턴으로 자동 로그인/로그아웃
async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
    params = LibraryHoldingsSearchParams(
        query="인공지능",
        results_per_page=20
    )
    
    results = await scraper.execute_holdings_search(params, max_results=10)
```

### 예시 2: 고급 검색 (OR/NOT 연산자)

```python
from library_holdings_scraper import (
    LibraryHoldingsScraper,
    LibraryHoldingsSearchParams,
    AdditionalQuery,
    QueryOperator,
    YearRange
)

async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
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
from library_holdings_scraper import LibraryHoldingsScraper, SearchField

async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
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
from library_holdings_scraper import LibraryHoldingsScraper, MaterialType

async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
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

## 소장자료 자동 검증

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

## 소장자료 복합 검색 예시

```python
async with LibraryHoldingsScraper(YONSEI_ID, YONSEI_PW) as scraper:
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

---

# 2. ElectronicResourceScraper (전자자료)

전자자료(학술논문, E-Journal 등)를 검색합니다.

## Pydantic 모델

### SearchField (Enum) - 전자자료용

전자자료 검색 필드를 정의합니다.

```python
class SearchField(str, Enum):
    KEYWORD = "TX"   # 키워드
    TOTAL = ""       # 전체
    TITLE = "TI"     # 제목
    AUTHOR = "AU"    # 저자
    SUBJECT = "SU"   # 주제어
```

### QueryOperator (Enum)

검색 연산자를 정의합니다.

```python
class QueryOperator(str, Enum):
    AND = "and"
    OR = "or"
    NOT = "not"
```

### AdditionalQuery (BaseModel) - 전자자료용

추가 검색 조건을 정의합니다.

```python
class AdditionalQuery(BaseModel):
    search_field: SearchField = Field(default=SearchField.TOTAL)
    query: str = Field(..., min_length=1)
    operator: QueryOperator = Field(default=QueryOperator.AND)
```

### YearRange (BaseModel)

발행 연도 범위를 정의합니다 (소장자료와 동일).

```python
class YearRange(BaseModel):
    from_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    to_year: Optional[int] = Field(default=None, ge=1900, le=2100)
```

### ElectronicSearchParams (BaseModel)

전자자료 검색 파라미터를 정의합니다.

```python
class ElectronicSearchParams(BaseModel):
    query: str                                      # 주 검색어 (필수)
    search_field: SearchField = SearchField.TOTAL   # 검색 필드
    additional_queries: List[AdditionalQuery] = []  # 추가 검색 조건 (최대 10개)
    year_range: Optional[YearRange] = None          # 발행 연도 범위
    results_per_page: Literal[10, 20, 30, 50, 100] = 20  # 페이지당 결과 수
    academic_journals_only: bool = True             # 학술저널만 검색
    foreign_language: bool = True                   # 외국어 자료 포함
```

## 전자자료 사용 예시

### 예시 1: 간단한 검색

```python
from electronic_resource_scraper import (
    ElectronicResourceScraper,
    ElectronicSearchParams,
    SearchField,
    YearRange
)

async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
    params = ElectronicSearchParams(
        query="machine learning",
        search_field=SearchField.KEYWORD,
        results_per_page=20,
        academic_journals_only=True,
        year_range=YearRange(from_year=2020, to_year=2025)
    )
    
    results = await scraper.execute_electronic_search(params, max_results=10)
    
    for result in results:
        print(f"제목: {result.title}")
        print(f"저자: {', '.join(result.author)}")
        print(f"출처: {result.source}")
        print(f"초록: {result.abstract[:100]}...")
        print(f"키워드: {', '.join(result.keywords)}")
```

### 예시 2: 고급 검색 (OR 연산자)

```python
from electronic_resource_scraper import (
    ElectronicSearchParams,
    SearchField,
    AdditionalQuery,
    QueryOperator,
    YearRange
)

async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
    params = ElectronicSearchParams(
        query="deep learning",
        search_field=SearchField.KEYWORD,
        additional_queries=[
            AdditionalQuery(
                query="neural networks",
                operator=QueryOperator.OR
            ),
            AdditionalQuery(
                query="computer vision",
                operator=QueryOperator.OR
            )
        ],
        results_per_page=20,
        academic_journals_only=True,
        year_range=YearRange(from_year=2022, to_year=2025)
    )
    
    results = await scraper.execute_electronic_search(params, max_results=10)
```

### 예시 3: 필드별 검색

```python
async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
    params = ElectronicSearchParams(
        query="artificial intelligence",
        search_field=SearchField.TITLE,  # 제목에서 검색
        additional_queries=[
            AdditionalQuery(
                search_field=SearchField.SUBJECT,
                query="ethics",
                operator=QueryOperator.AND
            ),
            AdditionalQuery(
                search_field=SearchField.AUTHOR,
                query="Russell",
                operator=QueryOperator.AND
            )
        ],
        results_per_page=30,
        academic_journals_only=True
    )
    
    results = await scraper.execute_electronic_search(params, max_results=5)
```

### 예시 4: 상세 정보 활용

```python
async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
    params = ElectronicSearchParams(
        query="quantum computing",
        search_field=SearchField.KEYWORD,
        results_per_page=10,
        academic_journals_only=True,
        year_range=YearRange(from_year=2023, to_year=2025)
    )
    
    # 자동으로 각 결과의 상세 정보(초록, 키워드, DOI 등)를 가져옴
    results = await scraper.execute_electronic_search(params, max_results=3)
    
    for result in results:
        print(f"\n{'='*80}")
        print(f"제목: {result.title}")
        print(f"저자: {', '.join(result.author)}")
        print(f"출처: {result.source}")
        print(f"발행년도: {result.publication_year}")
        print(f"DOI: {result.doi}")
        print(f"링크: {result.link_url}")
        print(f"\n초록:\n{result.abstract}")
        print(f"\n키워드: {', '.join(result.keywords)}")
```

### 예시 5: 언어 필터

```python
# 한국어 논문만 검색
async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
    params = ElectronicSearchParams(
        query="인공지능",
        search_field=SearchField.KEYWORD,
        results_per_page=20,
        academic_journals_only=True,
        foreign_language=False,  # 외국어 제외 (한국어만)
        year_range=YearRange(from_year=2020, to_year=2025)
    )
    
    results = await scraper.execute_electronic_search(params, max_results=10)
```

## 전자자료 자동 검증

Pydantic은 다음을 자동으로 검증합니다:

### 1. 연도 범위 검증

```python
# ❌ 오류: 종료 연도가 시작 연도보다 작음
params = ElectronicSearchParams(
    query="test",
    year_range=YearRange(from_year=2025, to_year=2020)
)
# ValueError: 종료 연도는 시작 연도보다 크거나 같아야 합니다
```

### 2. 검색어 길이 검증

```python
# ❌ 오류: 빈 검색어
params = ElectronicSearchParams(query="")
# ValidationError: String should have at least 1 character
```

### 3. 페이지당 결과 수 검증

```python
# ❌ 오류: 허용되지 않는 값
params = ElectronicSearchParams(
    query="test",
    results_per_page=25  # 10, 20, 30, 50, 100만 허용
)
# ValidationError: Input should be 10, 20, 30, 50 or 100
```

### 4. 추가 검색 조건 개수 검증

```python
# ❌ 오류: 추가 검색 조건이 10개를 초과
params = ElectronicSearchParams(
    query="test",
    additional_queries=[AdditionalQuery(query=f"query{i}") for i in range(11)]
)
# ValidationError: List should have at most 10 items after validation
```

## 전자자료 복합 검색 예시

```python
async with ElectronicResourceScraper(YONSEI_ID, YONSEI_PW) as scraper:
    params = ElectronicSearchParams(
        query="machine learning",
        search_field=SearchField.TITLE,
        additional_queries=[
            AdditionalQuery(
                search_field=SearchField.AUTHOR,
                query="Hinton",
                operator=QueryOperator.AND
            ),
            AdditionalQuery(
                search_field=SearchField.SUBJECT,
                query="neural networks",
                operator=QueryOperator.AND
            )
        ],
        year_range=YearRange(from_year=2020, to_year=2025),
        results_per_page=50,
        academic_journals_only=True,
        foreign_language=True
    )
    
    results = await scraper.execute_electronic_search(params, max_results=20)
```

---

# 환경 설정

## .env 파일 설정

로그인이 필요하므로 `.env` 파일을 생성하고 연세대 자격증명을 추가하세요:

```bash
# .env
YONSEI_ID=your_id
YONSEI_PW=your_password
```

## 필수 패키지 설치

```bash
pip install python-dotenv playwright beautifulsoup4 aiohttp pydantic
playwright install chromium
```

## 테스트

예시 파일을 실행하여 Pydantic 모델을 테스트할 수 있습니다:

```bash
cd backend/retrieval-service/search

# 소장자료 + 전자자료 통합 예시
python3 example_complete_usage.py

# 소장자료만
python3 example_usage.py

# 전자자료 파싱 테스트
python3 test_parse_electronic_results.py
```
