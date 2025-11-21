from typing import List
from google import genai
from config import settings
import logging
import json

from shared.models import RankedDocument, CRAGResult, RelevanceLevel

class RefinerService:
    """CRAG (Corrective RAG) - 검색 결과 품질 평가"""
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.CRAG_LLM_MODEL,
            generation_config={"response_mime_type": "application/json"}
        )
        self.logger = logging.getLogger(__name__)
    
    async def evaluate_relevance(
        self,
        documents: List[RankedDocument],
        user_query: str
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
                    doc, user_query
                )
                results.append(crag_result)
                
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
        query: str
    ) -> CRAGResult:
        """단일 문서 평가 (LLM 호출)"""
        
        prompt = f"""You are a document relevance evaluator.
다음 문서가 사용자 질문에 대한 답변을 제공하는지 평가하세요.

질문: {query}

문서 내용:
{doc.content[:1000]}

다음 중 하나로 판단하세요:
- CORRECT: 문서가 질문에 직접적으로 답변하고 관련성이 높음
- AMBIGUOUS: 문서가 부분적으로 관련되지만 추가 정보 필요
- INCORRECT: 문서가 질문과 무관하거나 오해의 소지가 있음

JSON 형식으로 응답:
{{
    "relevance": "CORRECT" | "AMBIGUOUS" | "INCORRECT",
    "confidence": 0.0~1.0,
    "reason": "판단 근거 (한 문장)"
}}"""
        
        response = await self.model.generate_content_async(prompt)
        
        # JSON 파싱
        result_text = response.text
        result_dict = json.loads(result_text)
        
        return CRAGResult(
            document=doc,
            relevance=RelevanceLevel(result_dict["relevance"].lower()),
            confidence=result_dict["confidence"],
            reason=result_dict.get("reason")
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
                if result.confidence >= settings.CRAG_RELEVANCE_THRESHOLD:
                    filtered.append(result.document)
                else:
                    self.logger.debug(
                        f"Filtered AMBIGUOUS doc (low confidence): "
                        f"{result.document.content[:50]}"
                    )
            
            # INCORRECT는 제외
        
        return filtered
    
    def needs_web_search(self, crag_results: List[CRAGResult]) -> bool:
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
        
        return incorrect_ratio > settings.CRAG_INCORRECT_RATIO_THRESHOLD
    
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