import aiohttp
from typing import Optional
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class BaseLibraryScraper:
    """모든 도서관 스크래퍼의 상위 클래스"""
    
    def __init__(self):
        self.base_url = "https://library.yonsei.ac.kr"
        self.login_url = f"{self.base_url}/login"
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
    
    async def perform_login(self, user_id: str, user_pw: str) -> bool:
        """
        1. Playwright를 사용하여 실제 브라우저에서 로그인을 수행
        2. 생성된 인증 쿠키를 aiohttp 세션으로 복사
        """
        logger.info(f"Starting login process for user: {user_id}")
        
        async with async_playwright() as p:
            # headless=False로 설정하면 브라우저가 뜨는 것을 눈으로 볼 수 있습니다 (디버깅용)
            browser = await p.chromium.launch(headless=True) 
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 1. 로그인 페이지 이동
                await page.goto(self.login_url)
                
                # 페이지 로딩 대기 (아이디 입력창이 나올 때까지)
                await page.wait_for_selector("#id", state="visible")

                # 2. 아이디/비번 입력 (제공해주신 HTML 기반)
                await page.fill("#id", user_id)
                await page.fill("#password", user_pw)

                # (선택사항) '로그인 유지' 체크박스 클릭
                # 체크하면 세션 유지 시간이 길어질 수 있어 추천합니다.
                if await page.is_visible("#keepLogin"):
                     await page.check("#keepLogin")

                # 3. 로그인 버튼 클릭
                # submit 타입의 input이므로 클릭 시 폼 전송이 일어남
                logger.info("Clicking login button...")
                
                # 클릭과 동시에 네비게이션(페이지 이동)이 일어날 것을 기다림
                async with page.expect_navigation(timeout=10000):
                    await page.click(".loginBtn input[type='submit']")

                # 4. 로그인 성공 확인
                # 보통 로그인 후에는 URL이 바뀌거나, 로그인 폼이 사라집니다.
                # 여기서는 간단히 쿠키가 생성되었는지로 1차 판단하거나, 
                # 페이지 내에 'Logout' 버튼이나 사용자 이름이 있는지 체크하는 것이 확실합니다.
                
                # 예시: 로그인 후 메인 페이지로 갔다면 URL 체크
                # if "login" not in page.url: ...

                # 5. 쿠키 추출 및 aiohttp 세션에 주입
                cookies = await context.cookies()
                session = await self._get_session()
                
                if not cookies:
                    logger.error("No cookies found after login attempt.")
                    return False

                for cookie in cookies:
                    # aiohttp 쿠키 저장소에 업데이트
                    session.cookie_jar.update_cookies({cookie['name']: cookie['value']})
                
                logger.info(f"Login successful. Transferred {len(cookies)} cookies to session.")
                return True

            except Exception as e:
                logger.error(f"Login failed due to error: {e}")
                return False
            finally:
                await browser.close()

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
