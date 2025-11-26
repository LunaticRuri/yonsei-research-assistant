from shared.models import RetrievalResult, RankedDocument
from generation_service.services.llm_client import LLMClient
from generation_service.prompts import SELF_RAG_SYSTEM_PROMPT, SELF_RAG_USER_PROMPT_TEMPLATE
from generation_service.models import GenerationResult
import logging

logger = logging.getLogger(__name__)

class GeneratorService:
    def __init__(self):
        self.llm_client = LLMClient()

    def _format_documents(self, documents: list[RankedDocument]) -> str:
        formatted_docs = []
        for idx, doc in enumerate(documents, 1):
            # Use metadata to provide context (title, author, etc.)
            title = doc.metadata.get("title", "No Title")
            author = doc.metadata.get("author", "Unknown Author")
            source = doc.source
            content = doc.content
            
            doc_str = f"Document [{idx}]\nTitle: {title}\nAuthor: {author}\nSource: {source}\nContent: {content}\n"
            formatted_docs.append(doc_str)
        
        return "\n".join(formatted_docs)

    async def generate(self, query: str, retrieval_result: RetrievalResult) -> GenerationResult:
        """
        Generate a response using Self-RAG approach.
        """
        documents = retrieval_result.documents
        
        if not documents:
            return GenerationResult(
                answer="죄송합니다. 관련 문서를 찾을 수 없어 답변을 생성할 수 없습니다.",
                citations=[],
                is_supported_score=0,
                is_useful_score=0,
                reasoning="No documents retrieved.",
                retrieval_metadata=retrieval_result.metadata
            )

        documents_text = self._format_documents(documents)
        
        user_prompt = SELF_RAG_USER_PROMPT_TEMPLATE.format(
            query=query,
            documents_text=documents_text
        )
        
        messages = [
            {"role": "system", "content": SELF_RAG_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response_data = await self.llm_client.generate_json(messages)
            
            # Validate and parse response
            result = GenerationResult(
                answer=response_data.get("answer", "답변 생성 실패"),
                citations=response_data.get("citations", []),
                is_supported_score=response_data.get("is_supported_score", 0),
                is_useful_score=response_data.get("is_useful_score", 0),
                reasoning=response_data.get("reasoning", ""),
                retrieval_metadata=retrieval_result.metadata
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return GenerationResult(
                answer="답변 생성 중 오류가 발생했습니다.",
                citations=[],
                is_supported_score=0,
                is_useful_score=0,
                reasoning=f"Error: {str(e)}",
                retrieval_metadata=retrieval_result.metadata
            )
