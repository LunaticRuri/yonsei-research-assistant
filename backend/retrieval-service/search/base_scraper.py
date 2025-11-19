import aiohttp
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BaseLibraryScraper:
    """모든 도서관 스크래퍼의 부모 클래스"""
    
    def __init__(self):
        self.base_url = "https://library.yonsei.ac.kr"
        self.request_delay = 1.0
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br'
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """aiohttp 세션 가져오기 또는 생성"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def _fetch(self, url: str) -> str:
        """공통 HTTP GET 요청 헬퍼"""
        session = await self._get_session()
        async with session.get(url, timeout=30) as response:
            response.raise_for_status()
            return await response.text()
