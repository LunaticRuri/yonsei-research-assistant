from shared.models import (
    RetrievalResult,
    RankedDocument,
    SelfRAGPromptType,
    GenerationResultType,
    GenerationResult
)
from generation_service.services.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)

class GeneratorService:
    def __init__(self):
        self.llm_client = LLMClient()

    def _format_documents(self, documents: list[RankedDocument]) -> str:
        formatted_docs = []
        
        for idx, doc in enumerate(documents, 1):
            metadata = doc.metadata or {}    
            metadata_str = "\n".join([f"{key}: {value}" for key, value in metadata.items()])
            # source = doc.source
            content = doc.content
            
            doc_str = f"--- Document [{idx}] ---\n{metadata_str}\nContent: {content}\n--- End of Document [{idx}] ---\n"
            formatted_docs.append(doc_str)
        return "\n".join(formatted_docs)
    
    async def generate_without_self_rag(self, query: str, retrieval_result: RetrievalResult) -> GenerationResult:
        """
        Generate a response without Self-RAG evaluation.
        """
        if retrieval_result.needs_requestioning:
            return GenerationResult(
                answer="질문을 다시 작성해 주세요. (CRAG 단계에서 재질문 필요하다고 판단함)",
                result_type=GenerationResultType.REQUESTIONING,
                reasoning="Requestioning needed.",
                retrieval_metadata=retrieval_result.metadata
            )
        
        documents = retrieval_result.documents
        
        if not documents:
            return GenerationResult(
                answer="죄송합니다. 관련 문서를 찾을 수 없어 답변을 생성할 수 없습니다. (문서 검색 결과 없음)",
                result_type=GenerationResultType.NO_DOCUMENTS,
                reasoning="No documents retrieved.",
                retrieval_metadata=retrieval_result.metadata
            )

        documents_text = self._format_documents(documents)
        
        try:
            final_answer = await self.llm_client.generate_final_response(
                query_text=query,
                documents_text=documents_text
            )
            
            return GenerationResult(
                answer=final_answer,
                result_type=GenerationResultType.ANSWER,
                reasoning="Generated answer without Self-RAG evaluation.",
                retrieval_metadata=retrieval_result.metadata
            )
        
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return GenerationResult(
                answer="답변 생성 중 오류가 발생했습니다.",
                result_type=GenerationResultType.ERROR,
                reasoning=f"Error: {str(e)}",
                retrieval_metadata=retrieval_result.metadata
            )
        
    async def generate(self, query: str, retrieval_result: RetrievalResult) -> GenerationResult:
        """
        Generate a response using Self-RAG approach.
        """

        # TODO: CLI Interface와 함께 생각해서 재질문 요청 구현 필요
        if retrieval_result.needs_requestioning:
            return GenerationResult(
                answer="질문을 다시 작성해 주세요. (CRAG 단계에서 재질문 필요하다고 판단함)",
                result_type=GenerationResultType.REQUESTIONING,
                reasoning="Requestioning needed.",
                retrieval_metadata=retrieval_result.metadata
            )

        documents = retrieval_result.documents
        
        if not documents:
            return GenerationResult(
                answer="죄송합니다. 관련 문서를 찾을 수 없어 답변을 생성할 수 없습니다. (문서 검색 결과 없음)",
                result_type=GenerationResultType.NO_DOCUMENTS,
                reasoning="No documents retrieved.",
                retrieval_metadata=retrieval_result.metadata
            )

        documents_text = self._format_documents(documents)
        try: 
            # SELF_RAG 평가
            # STEP 1: 관련성 평가
            is_relevant = self.llm_client.generate_self_rag_response(
                query_text=query,
                documents_text=documents_text,
                prompt_type=SelfRAGPromptType.RELEVANCE_CHECK
            )
            if not is_relevant:
                return GenerationResult(
                    answer="죄송합니다. 제공된 문서들이 질문과 관련이 없어 답변을 생성할 수 없습니다. (Self-RAG 관련성 평가 실패)",
                    result_type=GenerationResultType.NO_DOCUMENTS,
                    reasoning="Documents deemed irrelevant by Self-RAG.",
                    retrieval_metadata=retrieval_result.metadata
                )
            
            # STEP 2: (임시) 최종 답변 생성
            tmp_final_answer = await self.llm_client.generate_final_response(
                query_text=query,
                documents_text=documents_text
            )

            # STEP 3: 환각 평가
            correction_loop_counter = 0
            while True:
                is_accurate = await self.llm_client.generate_self_rag_response(
                    answer_text=tmp_final_answer,
                    documents_text=documents_text,
                    prompt_type=SelfRAGPromptType.HALLUCINATION_CHECK
                )
                correction_loop_counter += 1
                if is_accurate:
                    # STEP 4로 진행
                    break
                # NOTE: 환각으로 판단되면 답변 재생성, 최대 2회까지 재시도
                if not is_accurate and correction_loop_counter > 2:
                    return GenerationResult(
                        answer= f"죄송합니다. 생성된 답변이 정확하지 않아 제공할 수 없습니다. (Self-RAG 환각 평가 실패, {correction_loop_counter}회 재생성 시도)",
                        result_type=GenerationResultType.REQUESTIONING,
                        reasoning="Generated answer deemed hallucinatory by Self-RAG.",
                        retrieval_metadata=retrieval_result.metadata
                    )
            
            # STEP 4: 유용성 평가
            is_useful = await self.llm_client.generate_self_rag_response(
                query_text=query,
                answer_text=tmp_final_answer,
                prompt_type=SelfRAGPromptType.HELPFULNESS_CHECK
            )
            if not is_useful:
                return GenerationResult(
                    answer="죄송합니다. 생성된 답변이 유용하지 않아 제공할 수 없습니다. (Self-RAG 유용성 평가 실패)",
                    result_type=GenerationResultType.REQUESTIONING,
                    reasoning="Generated answer deemed unhelpful by Self-RAG.",
                    retrieval_metadata=retrieval_result.metadata
                )
            
            # STEP 5: 최종 답변 반환
            final_answer = tmp_final_answer

            return GenerationResult(
                answer=final_answer,
                result_type=GenerationResultType.ANSWER,
                reasoning="Generated answer passed all Self-RAG evaluations.",
                retrieval_metadata=retrieval_result.metadata
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return GenerationResult(
                answer="답변 생성 중 오류가 발생했습니다.",
                result_type=GenerationResultType.ERROR,
                citations=[],
                is_supported_score=0,
                is_useful_score=0,
                reasoning=f"Error: {str(e)}",
                retrieval_metadata=retrieval_result.metadata
            )
