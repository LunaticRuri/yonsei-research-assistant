from typing import List, Dict, Any
import re
from collections import Counter

class KeywordAnalyzer:
    """키워드 분석 및 확장 서비스"""
    
    def __init__(self):
        # 학문 분야별 키워드 매핑
        self.academic_field_keywords = {
            "psychology": ["심리", "인지", "행동", "정신", "사회심리"],
            "sociology": ["사회", "집단", "문화", "계층", "불평등"],
            "medicine": ["의학", "건강", "질병", "치료", "임상"],
            "education": ["교육", "학습", "교수", "학생", "학교"],
            "economics": ["경제", "시장", "금융", "투자", "소비"],
            "politics": ["정치", "정책", "정부", "권력", "민주주의"]
        }
        
        # 동의어 사전
        self.synonym_dict = {
            "불평등": ["격차", "차이", "불균형", "편차"],
            "수면": ["잠", "휴식", "수면패턴", "잠자리"],
            "스트레스": ["압박", "긴장", "부담", "심리적압박"],
            "교육": ["학습", "교수", "수업", "강의"],
            "경제": ["재정", "금융", "경제적", "소득"]
        }
    
    async def analyze_concepts(self, key_concepts: List[str], research_topic: str) -> Dict[str, Any]:
        """핵심 개념 분석"""
        
        # 키워드 정제
        cleaned_concepts = [self._clean_keyword(concept) for concept in key_concepts]
        
        # 주요 키워드 선별
        primary_keywords = self._select_primary_keywords(cleaned_concepts, research_topic)
        
        # 학문 분야 식별
        academic_fields = self._identify_academic_fields(primary_keywords + [research_topic])
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(primary_keywords, research_topic)
        
        return {
            "primary_keywords": primary_keywords,
            "academic_fields": academic_fields,
            "confidence": confidence,
            "keyword_types": self._classify_keywords(primary_keywords)
        }
    
    async def generate_expansion_keywords(
        self, 
        primary_keywords: List[str], 
        research_topic: str
    ) -> Dict[str, List[str]]:
        """확장 키워드 생성"""
        
        expansion_result = {
            "synonyms": [],
            "related_terms": [],
            "academic_terms": [],
            "academic_fields": []
        }
        
        # 동의어 확장
        for keyword in primary_keywords:
            synonyms = self._get_synonyms(keyword)
            expansion_result["synonyms"].extend(synonyms)
        
        # 관련 용어 생성
        related_terms = self._generate_related_terms(primary_keywords, research_topic)
        expansion_result["related_terms"] = related_terms
        
        # 학술 용어 추가
        academic_terms = self._generate_academic_terms(primary_keywords)
        expansion_result["academic_terms"] = academic_terms
        
        # 학문 분야 키워드
        fields = self._identify_academic_fields(primary_keywords + [research_topic])
        expansion_result["academic_fields"] = fields
        
        return expansion_result
    
    def _clean_keyword(self, keyword: str) -> str:
        """키워드 정제"""
        # 특수문자 제거, 공백 정리
        cleaned = re.sub(r'[^\w\s가-힣]', '', keyword)
        return cleaned.strip()
    
    def _select_primary_keywords(self, concepts: List[str], research_topic: str) -> List[str]:
        """주요 키워드 선별"""
        # 길이, 빈도, 중요도를 고려한 키워드 선별
        keywords = []
        
        # 연구 주제에서 핵심 단어 추출
        topic_words = self._extract_key_terms(research_topic)
        keywords.extend(topic_words[:3])  # 상위 3개
        
        # 개념 리스트에서 추가
        for concept in concepts:
            if concept and len(concept) > 2:  # 2글자 이상
                keywords.append(concept)
        
        # 중복 제거
        return list(set(keywords))[:5]  # 최대 5개
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """텍스트에서 핵심 용어 추출"""
        # 간단한 키워드 추출 로직
        # 실제로는 더 정교한 NLP 기법 사용 가능
        words = text.split()
        
        # 불용어 제거
        stopwords = ["이", "그", "저", "것", "에", "의", "를", "은", "는", "이다", "하다", "되다"]
        filtered_words = [word for word in words if word not in stopwords and len(word) > 1]
        
        # 빈도순 정렬
        word_freq = Counter(filtered_words)
        return [word for word, count in word_freq.most_common(10)]
    
    def _identify_academic_fields(self, keywords: List[str]) -> List[str]:
        """학문 분야 식별"""
        fields = []
        
        for field, field_keywords in self.academic_field_keywords.items():
            for keyword in keywords:
                if any(fk in keyword for fk in field_keywords):
                    fields.append(field)
                    break
        
        return list(set(fields))
    
    def _calculate_confidence(self, keywords: List[str], research_topic: str) -> float:
        """키워드 분석 신뢰도 계산"""
        base_confidence = 0.7
        
        # 키워드 수에 따른 가중치
        keyword_weight = min(len(keywords) * 0.05, 0.2)
        
        # 주제와 키워드 일치도
        topic_match = self._calculate_topic_keyword_match(keywords, research_topic)
        
        return min(base_confidence + keyword_weight + topic_match, 1.0)
    
    def _calculate_topic_keyword_match(self, keywords: List[str], research_topic: str) -> float:
        """주제와 키워드 일치도 계산"""
        matches = 0
        for keyword in keywords:
            if keyword in research_topic:
                matches += 1
        
        return (matches / len(keywords)) * 0.1 if keywords else 0
    
    def _get_synonyms(self, keyword: str) -> List[str]:
        """동의어 검색"""
        synonyms = []
        for key, values in self.synonym_dict.items():
            if key in keyword or keyword in key:
                synonyms.extend(values)
        
        return synonyms[:3]  # 최대 3개
    
    def _generate_related_terms(self, keywords: List[str], research_topic: str) -> List[str]:
        """관련 용어 생성"""
        # 간단한 관련 용어 생성 로직
        related = []
        
        # 학문적 접두사/접미사 추가
        academic_prefixes = ["사회적", "심리적", "경제적", "문화적"]
        academic_suffixes = ["현상", "요인", "영향", "관계", "분석"]
        
        for keyword in keywords[:2]:  # 상위 2개 키워드만
            for prefix in academic_prefixes:
                related.append(f"{prefix} {keyword}")
            
            for suffix in academic_suffixes:
                related.append(f"{keyword} {suffix}")
        
        return related[:5]  # 최대 5개
    
    def _generate_academic_terms(self, keywords: List[str]) -> List[str]:
        """학술적 용어 생성"""
        academic_terms = []
        
        # 일반적인 학술 용어들
        general_academic = [
            "요인 분석", "상관관계", "인과관계", "통계적 유의성",
            "질적 연구", "양적 연구", "실증 분석", "이론적 틀"
        ]
        
        # 키워드와 관련성이 높은 것들만 선별
        for term in general_academic:
            if any(kw in term for kw in keywords):
                academic_terms.append(term)
        
        return academic_terms[:3]  # 최대 3개
    
    def _classify_keywords(self, keywords: List[str]) -> Dict[str, List[str]]:
        """키워드 유형 분류"""
        classification = {
            "concepts": [],      # 개념어
            "phenomena": [],     # 현상어  
            "methods": [],       # 방법론어
            "subjects": []       # 대상어
        }
        
        # 간단한 분류 로직
        for keyword in keywords:
            if any(method_word in keyword for method_word in ["분석", "연구", "조사"]):
                classification["methods"].append(keyword)
            elif any(subject_word in keyword for subject_word in ["학생", "사람", "집단", "개인"]):
                classification["subjects"].append(keyword)
            elif any(concept_word in keyword for concept_word in ["불평등", "스트레스", "교육"]):
                classification["concepts"].append(keyword)
            else:
                classification["phenomena"].append(keyword)
        
        return classification