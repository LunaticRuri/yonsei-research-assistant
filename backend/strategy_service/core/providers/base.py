from abc import ABC, abstractmethod

class BaseAPIHandler(ABC):
    """
    모든 LLM API 핸들러가 상속받아야 하는 기본 클래스
    """
    @abstractmethod
    async def generate_keywords(self, query: str) -> str:
        """
        질문을 받아 검색 키워드 문자열을 반환해야 함.
        """
        pass
