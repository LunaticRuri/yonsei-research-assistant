#**********************************************
# DEPRICIATED!
#**********************************************
from typing import List, Dict, Any
from shared.models import SearchStrategyResponse, SearchStrategy # (이건 backend/에서 실행해서 OK)
from .keyword_analyzer import KeywordAnalyzer # <--- 1번 수정! (같은 폴더에 있다는 뜻)
from ..database import get_redis_connection # <--- 2번 수정! (부모 폴더에 있다는 뜻)

class StrategyEngine:
    """검색 전략 생성 및 관리 엔진 (Redis 연동)"""
    
    def __init__(self, keyword_analyzer: KeywordAnalyzer):
        self.keyword_analyzer = keyword_analyzer
        self.db = get_redis_connection() # --- [변경] Redis 연결 가져오기
        # --- [삭제] self.strategies = {} ---
    
    async def generate_initial_strategy(
        self,
        session_id: str,
        conversation_summary: str,
        research_topic: str,
        key_concepts: List[str]
    ) -> SearchStrategyResponse:
        """초기 검색 전략 생성"""
        keyword_analysis = await self.keyword_analyzer.analyze_concepts(
            key_concepts, research_topic
        )
        expansion_keywords = await self.keyword_analyzer.generate_expansion_keywords(
            keyword_analysis["primary_keywords"], research_topic
        )
        
        combined_expansion_keywords = list(set(expansion_keywords["synonyms"] + expansion_keywords["related_terms"]))
        
        boolean_query = self._create_boolean_query(
            keyword_analysis["primary_keywords"], 
            combined_expansion_keywords
        )
        
        strategy = SearchStrategy(
            primary_keywords=keyword_analysis["primary_keywords"],
            expansion_keywords=combined_expansion_keywords,
            boolean_query=boolean_query,
            rationale=self._generate_rationale(keyword_analysis),
            academic_fields=keyword_analysis["academic_fields"],
            suggested_databases=self._suggest_databases(research_topic)
        )
        
        # --- [변경] 메모리 대신 Redis에 저장 ---
        # Pydantic 모델을 JSON 문자열로 변환하여 저장, 24시간 후 자동 소멸
        strategy_json = strategy.model_dump_json()
        self.db.set(f"strategy:{session_id}", strategy_json, ex=86400)
        # ------------------------------------
        
        return SearchStrategyResponse(
            session_id=session_id,
            strategy=strategy,
            confidence_score=keyword_analysis["confidence"],
            alternative_approaches=self._generate_alternatives(keyword_analysis)
        )
    
    async def update_strategy(
        self,
        session_id: str,
        current_strategy: SearchStrategy,
        user_modifications: Dict[str, Any],
        feedback: str
    ) -> SearchStrategyResponse:
        """사용자 피드백을 바탕으로 전략 업데이트"""
        updated_strategy = current_strategy.model_copy(deep=True)
        
        if "add_keywords" in user_modifications:
            updated_strategy.primary_keywords.extend(user_modifications["add_keywords"])
        
        if "remove_keywords" in user_modifications:
            for keyword in user_modifications["remove_keywords"]:
                if keyword in updated_strategy.primary_keywords:
                    updated_strategy.primary_keywords.remove(keyword)
        
        if "modify_boolean" in user_modifications:
            updated_strategy.boolean_query = user_modifications["modify_boolean"]
        
        if not user_modifications.get("modify_boolean"):
            updated_strategy.boolean_query = self._create_boolean_query(
                updated_strategy.primary_keywords,
                updated_strategy.expansion_keywords
            )
        
        updated_strategy.rationale = self._update_rationale(updated_strategy, feedback)
        
        # --- [변경] 수정된 전략을 Redis에 다시 저장 ---
        strategy_json = updated_strategy.model_dump_json()
        self.db.set(f"strategy:{session_id}", strategy_json, ex=86400)
        # -----------------------------------------

        return SearchStrategyResponse(
            session_id=session_id,
            strategy=updated_strategy,
            confidence_score=0.95,  # 사용자 개입으로 신뢰도 증가
            alternative_approaches=[]
        )
    
    async def validate_strategy(self, session_id: str) -> Dict[str, Any]:
        """전략 유효성 검증 (Redis에서 조회)"""
        # --- [변경] 메모리 대신 Redis에서 조회 ---
        strategy_json = self.db.get(f"strategy:{session_id}")
        if not strategy_json:
            return {"valid": False, "error": "Strategy not found in Redis"}
        
        strategy = SearchStrategy.model_validate_json(strategy_json)
        # ------------------------------------

        validation_result = {
            "valid": True,
            "keyword_count": len(strategy.primary_keywords),
            "boolean_complexity": self._assess_boolean_complexity(strategy.boolean_query),
            "coverage_assessment": self._assess_coverage(strategy),
            "recommendations": []
        }
        
        if len(strategy.primary_keywords) < 2:
            validation_result["recommendations"].append("더 많은 핵심 키워드를 추가하는 것을 권장합니다.")
        
        return validation_result
    
    def _create_boolean_query(self, primary_keywords: List[str], expansion_keywords: List[str]) -> str:
        """불리언 검색식 생성"""
        if not primary_keywords:
            return ""
        
        primary_part = " OR ".join([f'"{kw}"' for kw in primary_keywords])
        
        if expansion_keywords:
            # 확장 키워드는 최대 3개까지만 사용하여 쿼리가 너무 복잡해지는 것을 방지
            expansion_part = " OR ".join([f'"{kw}"' for kw in expansion_keywords[:3]])
            return f"({primary_part}) AND ({expansion_part})"
        
        return f"({primary_part})"
    
    def _generate_rationale(self, keyword_analysis: Dict[str, Any]) -> str:
        """전략 근거 생성"""
        return f"""
        이 검색 전략은 다음과 같은 근거로 구성되었습니다:
        1. 핵심 키워드: {', '.join(keyword_analysis['primary_keywords'])} - 연구 주제의 핵심 개념을 직접적으로 반영
        2. 확장 키워드 선택 기준: 학술적 맥락에서 자주 사용되는 관련 용어 및 동의어
        3. 불리언 검색식: AND/OR 연산자를 활용한 정밀도와 재현율의 균형
        """
    
    def _update_rationale(self, strategy: SearchStrategy, feedback: str) -> str:
        """사용자 피드백을 반영한 근거 업데이트"""
        return f"""
        사용자 피드백 '{feedback}'을 반영하여 업데이트된 검색 전략입니다.
        최종 키워드: {', '.join(strategy.primary_keywords)}
        최종 검색식: {strategy.boolean_query}
        """
    
    def _suggest_databases(self, research_topic: str) -> List[str]:
        """연구 주제에 따른 추천 데이터베이스"""
        # 이 부분은 추후 LLM을 통해 동적으로 추천하도록 개선할 수 있습니다.
        return ["KISS", "DBpia", "RISS", "Web of Science", "PubMed"]
    
    def _generate_alternatives(self, keyword_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """대안적 접근법 제안"""
        return [
            {"approach": "broader_search", "description": "더 넓은 범위의 검색을 위해 상위 개념 키워드 사용"},
            {"approach": "narrower_search", "description": "더 구체적인 검색을 위해 하위 개념 키워드 사용"}
        ]
    
    def _assess_boolean_complexity(self, boolean_query: str) -> str:
        """불리언 쿼리 복잡도 평가"""
        if "AND" in boolean_query and "OR" in boolean_query:
            return "complex"
        elif "AND" in boolean_query or "OR" in boolean_query:
            return "moderate"
        return "simple"
    
    def _assess_coverage(self, strategy: SearchStrategy) -> str:
        """검색 범위 평가"""
        keyword_count = len(strategy.primary_keywords) + len(strategy.expansion_keywords)
        if keyword_count >= 10:
            return "comprehensive"
        elif keyword_count >= 5:
            return "adequate"
        return "limited"