"""
공통 검색 파라미터 모델
"""
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional, Union, TypeVar, Generic
import numpy as np

from shared.models import LibrarySearchField, ElectronicSearchField

class QueryOperator(str, Enum):
    """검색 연산자 (모든 스크래퍼 공통)"""
    AND = "and"
    OR = "or"
    NOT = "not"


class YearRange(BaseModel):
    """발행 연도 범위 (모든 스크래퍼 공통)"""
    from_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="시작 연도"
    )
    to_year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="종료 연도"
    )
    
    @field_validator('to_year')
    @classmethod
    def validate_year_range(cls, v, info):
        """종료 연도가 시작 연도보다 크거나 같은지 검증"""
        if v is not None and info.data.get('from_year') is not None:
            if v < info.data['from_year']:
                raise ValueError('종료 연도는 시작 연도보다 크거나 같아야 합니다')
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"from_year": 2020, "to_year": 2025}
            ]
        }
    }


# Generic 타입을 위한 타입 변수
SearchFieldType = TypeVar('SearchFieldType', bound=Enum)

class AdditionalQuery(BaseModel, Generic[SearchFieldType]):
    """
    추가 검색 조건
    """
    search_field: Union[str, LibrarySearchField, ElectronicSearchField] = Field(
        ...,
        description="검색 필드"
    )
    query: str = Field(
        ...,
        min_length=1,
        description="검색어"
    )
    operator: QueryOperator = Field(
        default=QueryOperator.AND,
        description="검색어와의 연산자 (AND, OR, NOT)"
    )
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "examples": [
                {
                    "search_field": "AUTHOR",
                    "query": "김철수",
                    "operator": "AND"
                }
            ]
        }
    }


# ============================================================================
# 기본 검색 파라미터 (추상 클래스)
# ============================================================================

class BaseSearchParams(BaseModel):
    """
    도서관 검색 파라미터의 기본 클래스
    
    공통 필드들을 정의하며, 각 스크래퍼는 이를 상속하여
    특화된 검색 파라미터를 구현합니다.
    """
    # 필수 파라미터
    query: str = Field(
        ...,
        min_length=1,
        description="주 검색어"
    )

    search_field: SearchFieldType = Field(
        default=None,
        description="검색 필드"
    )

    model_config = {
        "arbitrary_types_allowed": True
    }

# ============================================================================
# Vector DB 검색 파라미터
# ============================================================================

class VectorSearchParams(BaseModel):
    """
    Vector DB 검색을 위한 파라미터
    NOTE: BaseSearchParams와 별도임!
    """
    query_1: str
    vector_1: np.ndarray
    query_2: Optional[str] = None
    vector_2: Optional[np.ndarray] = None
    query_3: Optional[str] = None
    vector_3: Optional[np.ndarray] = None
    year_range: Optional[YearRange] = Field(
        default=None,
        description="발행 연도 범위"
    )

    model_config = {
        "arbitrary_types_allowed": True
    }
