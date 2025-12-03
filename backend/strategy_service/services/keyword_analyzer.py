#**********************************************
# DEPRICIATED!
#**********************************************
from typing import List, Dict, Any
import re
from collections import Counter
from .llm_client import LLMClient

class KeywordAnalyzer:
    """키워드 분석 및 확장 서비스 (LLM 연동)"""

    def __init__(self):
        """초기화: LLM 클라이언트 인스턴스 생성"""
        self.llm_client = LLMClient()
        # --- [삭제] 기존 규칙 기반 사전들은 모두 삭제합니다.

    async def analyze_concepts(self, key_concepts: List[str], research_topic: str) -> Dict[str, Any]:
        """핵심 개념 분석 (LLM 기반 학문 분야 식별 포함)"""
        cleaned_concepts = [self._clean_keyword(concept) for concept in key_concepts]
        primary_keywords = self._select_primary_keywords(cleaned_concepts, research_topic)
        
        # --- [변경] 학문 분야 식별을 LLM 호출로 변경 ---
        academic_fields = await self._identify_academic_fields(primary_keywords, research_topic)
        
        confidence = self._calculate_confidence(primary_keywords, research_topic)

        return {
            "primary_keywords": primary_keywords,
            "academic_fields": academic_fields,
            "confidence": confidence,
            "keyword_types": self._classify_keywords(primary_keywords) # 이 부분은 간단한 규칙 기반으로 유지
        }

    async def generate_expansion_keywords(
        self,
        primary_keywords: List[str],
        research_topic: str
    ) -> Dict[str, List[str]]:
        """확장 키워드 생성 (LLM 기반 동의어 및 관련어 확장)"""
        
        # --- [변경] 동의어와 관련어를 병렬로 호출하여 성능 최적화 ---
        import asyncio
        synonyms_task = self._get_synonyms_from_llm(primary_keywords, research_topic)
        related_terms_task = self._generate_related_terms(primary_keywords, research_topic)
        
        synonyms_results, related_terms_results = await asyncio.gather(
            synonyms_task,
            related_terms_task
        )
        # -----------------------------------------------------------

        expansion_result = {
            "synonyms": list(set(synonyms_results)),
            "related_terms": related_terms_results,
            "academic_terms": [], # 이 로직은 단순화/삭제 또는 추후 개선
            "academic_fields": [] # analyze_concepts에서 처리하므로 여기서 제외
        }

        return expansion_result

    async def _get_synonyms_from_llm(self, keywords: List[str], research_topic: str) -> List[str]:
        """LLM을 이용해 여러 키워드에 대한 동의어를 가져옵니다."""
        import asyncio
        tasks = [self.llm_client.generate_synonyms(kw, research_topic) for kw in keywords]
        results = await asyncio.gather(*tasks)
        # results는 [[동의어1, 동의어2], [동의어3]] 형태의 리스트이므로 단일 리스트로 펼칩니다.
        return [synonym for sublist in results for synonym in sublist]
        
    # --- [변경] 관련어 생성 함수를 LLM 호출로 변경 ---
    async def _generate_related_terms(self, keywords: List[str], research_topic: str) -> List[str]:
        """LLM을 이용해 관련어를 생성합니다."""
        return await self.llm_client.generate_related_terms(keywords, research_topic)

    # --- [변경] 학문 분야 식별 함수를 LLM 호출로 변경 ---
    async def _identify_academic_fields(self, keywords: List[str], research_topic: str) -> List[str]:
        """LLM을 이용해 학문 분야를 식별합니다."""
        return await self.llm_client.identify_academic_fields(keywords, research_topic)

    # 아래 함수들은 규칙 기반으로 유지합니다.
    def _clean_keyword(self, keyword: str) -> str:
        cleaned = re.sub(r'[^\w\s가-힣]', '', keyword)
        return cleaned.strip()

    def _select_primary_keywords(self, concepts: List[str], research_topic: str) -> List[str]:
        keywords = []
        topic_words = self._extract_key_terms(research_topic)
        keywords.extend(topic_words[:3])

        for concept in concepts:
            if concept and len(concept) > 2:
                keywords.append(concept)

        return list(set(keywords))[:5]

    def _extract_key_terms(self, text: str) -> List[str]:
        words = text.split()
        stopwords = ["이", "그", "저", "것", "에", "의", "를", "은", "는", "이다", "하다", "되다"]
        filtered_words = [word for word in words if word not in stopwords and len(word) > 1]
        word_freq = Counter(filtered_words)
        return [word for word, count in word_freq.most_common(10)]

    def _calculate_confidence(self, keywords: List[str], research_topic: str) -> float:
        base_confidence = 0.7
        keyword_weight = min(len(keywords) * 0.05, 0.2)
        topic_match = self._calculate_topic_keyword_match(keywords, research_topic)
        return min(base_confidence + keyword_weight + topic_match, 1.0)

    def _calculate_topic_keyword_match(self, keywords: List[str], research_topic: str) -> float:
        matches = 0
        for keyword in keywords:
            if keyword in research_topic:
                matches += 1
        return (matches / len(keywords)) * 0.1 if keywords else 0
        
    def _classify_keywords(self, keywords: List[str]) -> Dict[str, List[str]]:
        classification = { "concepts": [], "phenomena": [], "methods": [], "subjects": [] }
        for keyword in keywords:
            if any(word in keyword for word in ["분석", "연구", "조사"]):
                classification["methods"].append(keyword)
            elif any(word in keyword for word in ["학생", "사람", "집단", "개인"]):
                classification["subjects"].append(keyword)
            elif any(word in keyword for word in ["불평등", "스트레스", "교육"]):
                classification["concepts"].append(keyword)
            else:
                classification["phenomena"].append(keyword)
        return classification