from typing import List, Dict, Any
from shared.models import SearchStrategyResponse, SearchStrategy
from .keyword_analyzer import KeywordAnalyzer
import uuid

class StrategyEngine:
    """검색 전략 생성 및 관리 엔진"""
    
    def __init__(self, keyword_analyzer: KeywordAnalyzer):
        self.keyword_analyzer = keyword_analyzer
        self.strategies = {}  # 세션별 전략 저장
    
    async def generate_initial_strategy(
        self,
        session_id: str,
        conversation_summary: str,
        research_topic: str,
        key_concepts: List[str]
    ) -> SearchStrategyResponse:
        """초기 검색 전략 생성"""
        
        # 키워드 분석
        keyword_analysis = await self.keyword_analyzer.analyze_concepts(
            key_concepts, research_topic
        )
        
        # 주요 키워드 추출
        primary_keywords = keyword_analysis["primary_keywords"]
        
        # 확장 키워드 생성
        expansion_keywords = await self.keyword_analyzer.generate_expansion_keywords(
            primary_keywords, research_topic
        )
        
        # 불리언 검색식 생성
        boolean_query = self._create_boolean_query(primary_keywords, expansion_keywords)
        
        # 전략 객체 생성
        strategy = SearchStrategy(
            primary_keywords=primary_keywords,
            expansion_keywords=expansion_keywords["synonyms"],
            boolean_query=boolean_query,
            rationale=self._generate_rationale(keyword_analysis),
            academic_fields=expansion_keywords["academic_fields"],
            suggested_databases=self._suggest_databases(research_topic)
        )
        
        # 세션에 저장
        self.strategies[session_id] = strategy
        
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
        
        # 현재 전략을 기반으로 수정
        updated_strategy = current_strategy.copy()
        
        # 사용자 수정사항 적용
        if "add_keywords" in user_modifications:
            updated_strategy.primary_keywords.extend(user_modifications["add_keywords"])
        
        if "remove_keywords" in user_modifications:
            for keyword in user_modifications["remove_keywords"]:
                if keyword in updated_strategy.primary_keywords:
                    updated_strategy.primary_keywords.remove(keyword)
        
        if "modify_boolean" in user_modifications:
            updated_strategy.boolean_query = user_modifications["modify_boolean"]
        
        # 불리언 쿼리 재생성
        if not user_modifications.get("modify_boolean"):
            updated_strategy.boolean_query = self._create_boolean_query(
                updated_strategy.primary_keywords,
                updated_strategy.expansion_keywords
            )
        
        # 근거 업데이트
        updated_strategy.rationale = self._update_rationale(
            updated_strategy, feedback
        )
        
        # 세션에 저장
        self.strategies[session_id] = updated_strategy
        
        return SearchStrategyResponse(
            session_id=session_id,
            strategy=updated_strategy,
            confidence_score=0.85,  # 사용자 개입으로 신뢰도 증가
            alternative_approaches=[]
        )
    
    async def validate_strategy(self, session_id: str) -> Dict[str, Any]:
        """전략 유효성 검증"""
        strategy = self.strategies.get(session_id)
        if not strategy:
            return {"valid": False, "error": "Strategy not found"}
        
        validation_result = {
            "valid": True,
            "keyword_count": len(strategy.primary_keywords),
            "boolean_complexity": self._assess_boolean_complexity(strategy.boolean_query),
            "coverage_assessment": self._assess_coverage(strategy),
            "recommendations": []
        }
        
        # 키워드 수 검증
        if len(strategy.primary_keywords) < 2:
            validation_result["recommendations"].append(
                "더 많은 핵심 키워드를 추가하는 것을 권장합니다."
            )
        
        return validation_result
    
    def _create_boolean_query(self, primary_keywords: List[str], expansion_keywords: List[str]) -> str:
        """불리언 검색식 생성"""
        if not primary_keywords:
            return ""
        
        # 주요 키워드를 OR로 연결
        primary_part = " OR ".join([f'"{kw}"' for kw in primary_keywords])
        
        # 확장 키워드가 있으면 AND로 추가
        if expansion_keywords:
            expansion_part = " OR ".join([f'"{kw}"' for kw in expansion_keywords[:3]])
            return f"({primary_part}) AND ({expansion_part})"
        
        return f"({primary_part})"
    
    def _generate_rationale(self, keyword_analysis: Dict[str, Any]) -> str:
        """전략 근거 생성"""
        return f"""
        이 검색 전략은 다음과 같은 근거로 구성되었습니다:
        
        1. 핵심 키워드: {', '.join(keyword_analysis['primary_keywords'])}
           - 연구 주제의 핵심 개념을 직접적으로 반영
        
        2. 확장 키워드 선택 기준:
           - 학술적 맥락에서 자주 사용되는 관련 용어
           - 검색 범위 확장을 통한 누락 방지
        
        3. 불리언 검색식:
           - AND/OR 연산자를 활용한 정밀도와 재현율의 균형
        """
    
    def _update_rationale(self, strategy: SearchStrategy, feedback: str) -> str:
        """사용자 피드백을 반영한 근거 업데이트"""
        return f"""
        사용자 피드백을 반영하여 업데이트된 검색 전략:
        
        수정 내용: {feedback}
        
        최종 키워드: {', '.join(strategy.primary_keywords)}
        최종 검색식: {strategy.boolean_query}
        """
    
    def _suggest_databases(self, research_topic: str) -> List[str]:
        """연구 주제에 따른 추천 데이터베이스"""
        # TODO: 주제 분야별 데이터베이스 매핑 로직
        return ["KISS", "DBpia", "RISS", "Web of Science", "PubMed"]
    
    def _generate_alternatives(self, keyword_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """대안적 접근법 제안"""
        return [
            {
                "approach": "broader_search",
                "description": "더 넓은 범위의 검색을 위해 상위 개념 키워드 사용"
            },
            {
                "approach": "narrower_search", 
                "description": "더 구체적인 검색을 위해 하위 개념 키워드 사용"
            }
        ]
    
    def _assess_boolean_complexity(self, boolean_query: str) -> str:
        """불리언 쿼리 복잡도 평가"""
        if "AND" in boolean_query and "OR" in boolean_query:
            return "complex"
        elif "AND" in boolean_query or "OR" in boolean_query:
            return "moderate"
        else:
            return "simple"
    
    def _assess_coverage(self, strategy: SearchStrategy) -> str:
        """검색 범위 평가"""
        keyword_count = len(strategy.primary_keywords) + len(strategy.expansion_keywords)
        if keyword_count >= 8:
            return "comprehensive"
        elif keyword_count >= 5:
            return "adequate"
        else:
            return "limited"