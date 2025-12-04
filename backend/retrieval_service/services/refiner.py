from typing import List
from google import genai
from google.genai import types
from retrieval_service.config import retrieval_settings
import logging

from shared.models import RankedDocument, AnalysisUserQuery, CRAGResult, RelevanceLevel, GeneratedCRAGResponse
from shared.config import settings



class RefinerService:
    """CRAG (Corrective RAG) - 검색 결과 품질 평가"""
    
    def __init__(self):
        
        self.client = genai.Client(api_key=retrieval_settings.GEMINI_API_KEY)
        self.model_name = retrieval_settings.CRAG_LLM_MODEL
        
        self.relevance_threshold = retrieval_settings.CRAG_RELEVANCE_THRESHOLD
        self.incorrect_ratio_threshold = retrieval_settings.CRAG_INCORRECT_RATIO_THRESHOLD
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(settings.console_handler)
        self.logger.addHandler(settings.file_handler)
    
    async def analyze_user_query(
        self,
        user_query: str
    ) -> AnalysisUserQuery:
        """
        사용자 쿼리를 '주제', '의도', '제약' 관점으로 분해
        
        Returns:
            AnalysisUserQuery: 분해된 사용자 쿼리 요소
        """
        prompt = f"""
        너는 사용자의 정보 요구를 분석하는 전문가이다.
        다음 사용자 쿼리를 'subject(주제)', 'intention(의도)', 'restriction(제약)' 관점으로 분해하여 각각 간략히 설명하라.

        사용자 쿼리: {user_query}
        """
        
        response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=AnalysisUserQuery
                )
            )
        
        analysis = response.parsed
        return analysis
    
    async def evaluate_relevance(
        self,
        documents: List[RankedDocument],
        analyzed_user_query: AnalysisUserQuery
    ) -> List[CRAGResult]:
        """
        각 문서의 관련성을 CORRECT/AMBIGUOUS/INCORRECT로 평가
        
        Returns:
            CRAG 평가 결과 (문서 순서 유지)
        """
        results = []
        
        for doc in documents:
            try:
                crag_result = await self._evaluate_single_document(
                    doc, analyzed_user_query
                )
                results.append(crag_result)
                self.logger.info(
                    f"Evaluated doc: {doc.content[:50]}... "
                    f"as {crag_result.relevance} "
                    f"(confidence: {crag_result.confidence})"
                )
                
            except Exception as e:
                self.logger.error(f"CRAG evaluation failed: {e}")
                # 실패 시 AMBIGUOUS로 처리
                results.append(CRAGResult(
                    document=doc,
                    relevance=RelevanceLevel.AMBIGUOUS,
                    confidence=0.5,
                    reason="Evaluation failed"
                ))
        
        self._log_statistics(results)
        return results
    
    async def _evaluate_single_document(
        self,
        doc: RankedDocument,
        user_query: str
    ) -> CRAGResult:
        """단일 문서 평가 (LLM 호출)"""
        
        prompt = f"""
        너는 사용자의 정보 문제를 해결하기 위해 문서의 관련성을 평가하는 전문가이다.
        다음 문서가 소개하는 자료(책, 논문 등)가 사용자의 정보 질문을 해결할 수 있을지를 추측하여 평가하라.
        사용자의 질문은 subject(주제), intention(의도), restriction(제약) 관점에서 분석되었고, 이를 고려하여 평가해야 한다.
        1. relevance는 다음 세 가지 값 중 하나여야 한다. 판단 기준은 각각 다음과 같다:
            - CORRECT: 문서가 소개하는 자료가 질문과 관련성이 높아 문제를 해결할 가능성이 높음. 사용자의 의도와도 부합함
            - AMBIGUOUS: 문서가 소개하는 자료가 부분적으로 관련성이 있고, 문제 해결에 간접적으로 도움이 될 수도 있음. 사용자의 의도와 일부 부합함.
            - INCORRECT: 문서가 소개하는 자료가 질문과 무관하거나 오해의 소지가 있음. 사용자의 의도와 부합하지 않음. 사용자의 제약 조건을 충족하지 않으면 INCORRECT로 판단하라.
        2. confidence는 0.0에서 1.0 사이의 값으로, 너의 판단이 얼마나 확신하는지를 나타낸다.
        3. reason에는 너의 판단 근거를 간략히 서술하라.

        질문: {user_query}
        메타데이터: {doc.metadata}
        문서 내용:
        {doc.content[:1000]}
        """
        
        response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=GeneratedCRAGResponse
                )
            )
        
        result_elem = response.parsed
        
        return CRAGResult(
            document=doc,
            relevance=result_elem.relevance,
            confidence=result_elem.confidence,
            reason=result_elem.reason
        )
    
    def filter_by_quality(
        self,
        crag_results: List[CRAGResult]
    ) -> List[RankedDocument]:
        """
        CRAG 평가 기반 문서 필터링
        
        - CORRECT: 그대로 사용
        - AMBIGUOUS: confidence가 임계값 이상이면 포함
        - INCORRECT: 제거
        """
        filtered = []
        
        for result in crag_results:
            if result.relevance == RelevanceLevel.CORRECT:
                filtered.append(result.document)
            
            elif result.relevance == RelevanceLevel.AMBIGUOUS:
                if result.confidence >= self.relevance_threshold:
                    filtered.append(result.document)
                else:
                    self.logger.info(
                        f"Filtered AMBIGUOUS doc (low confidence): "
                        f"{result.document.content[:50]}"
                    )
            
            # INCORRECT는 제외
        
        return filtered
    
    def needs_requestioning(self, crag_results: List[CRAGResult]) -> bool:
        """
        INCORRECT 비율이 높으면 외부 웹 검색 필요 신호
        """
        if not crag_results:
            return True
        
        incorrect_count = sum(
            1 for r in crag_results 
            if r.relevance == RelevanceLevel.INCORRECT
        )
        
        incorrect_ratio = incorrect_count / len(crag_results)
        
        return incorrect_ratio > self.incorrect_ratio_threshold
    
    def _log_statistics(self, results: List[CRAGResult]):
        """평가 통계 로깅"""
        total = len(results)
        correct = sum(1 for r in results if r.relevance == RelevanceLevel.CORRECT)
        ambiguous = sum(1 for r in results if r.relevance == RelevanceLevel.AMBIGUOUS)
        incorrect = sum(1 for r in results if r.relevance == RelevanceLevel.INCORRECT)
        
        self.logger.info(
            f"CRAG Evaluation: CORRECT={correct}, "
            f"AMBIGUOUS={ambiguous}, INCORRECT={incorrect} "
            f"(Total={total})"
        )