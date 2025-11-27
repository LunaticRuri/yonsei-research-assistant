import aiohttp
from typing import Optional
import logging
import re
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BaseLibraryScraper:
    """모든 도서관 스크래퍼의 상위 클래스"""
    
    def __init__(self):
        self.is_logged_in = False

        self.base_url = "https://library.yonsei.ac.kr"
        self.login_url = f"{self.base_url}/login"
        self.logout_url = f"{self.base_url}/SSOLegacy.do?pname=spLogout"

        # TODO: 적절한 값으로 설정 필요. 일단은 안전하게 1초로 설정함.
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
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(headers=self.headers, connector=connector)
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
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            try:
                # 1. 로그인 페이지 이동
                await page.goto(self.login_url)
                
                # 페이지 로딩 대기
                await page.wait_for_selector("#id", state="visible")

                # 2. 아이디/비번 입력
                await page.fill("#id", user_id)
                await page.fill("#password", user_pw)

                # '로그인 유지' 체크박스 클릭
                if await page.is_visible("#keepLogin"):
                     await page.check("#keepLogin")

                # 3. 로그인 버튼 클릭
                # submit 타입의 input이므로 클릭 시 폼 전송이 일어남
                logger.info("Clicking login button...")
                
                # 클릭과 동시에 네비게이션(페이지 이동)이 일어날 것을 기다림
                async with page.expect_navigation(timeout=10000):
                    await page.click(".loginBtn input[type='submit']")

                # 4. 로그인 성공 확인
                
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
                
                self.is_logged_in = True  # 로그인 상태 설정
                logger.info(f"Login successful. Transferred {len(cookies)} cookies to session.")
                return True

            except Exception as e:
                logger.error(f"Login failed due to error: {e}")
                self.is_logged_in = False
                return False
            finally:
                await browser.close()

    async def perform_logout(self) -> bool:
        """
        로그아웃 수행: 연세대 도서관 로그아웃 URL에 요청을 보내 서버 측 세션 종료
        """
        if not self.is_logged_in:
            logger.info("Not logged in, skipping logout.")
            return True
            
        try:
            logger.info("Performing logout...")
            session = await self._get_session()
            
            # 로그아웃 URL로 GET 요청
            async with session.get(self.logout_url, timeout=10) as response:
                if response.status in [200, 302, 303]:  # 성공 또는 리다이렉트
                    logger.info(f"Logout successful (status: {response.status}).")
                    self.is_logged_in = False
                    
                    # 쿠키 클리어
                    session.cookie_jar.clear()
                    return True
                else:
                    logger.warning(f"Logout returned unexpected status: {response.status}")
                    self.is_logged_in = False  # 상태는 초기화
                    return False
                    
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            self.is_logged_in = False  # 에러 발생 시에도 상태 초기화
            return False

    async def __aenter__(self):
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        async with 블록이 끝날 때 호출됨.
        로그인 상태라면 로그아웃 수행 후 세션 정리.
        """
        # 로그인 상태라면 로그아웃 수행
        if self.is_logged_in:
            await self.perform_logout()
        
        # 세션 종료
        await self.close()
        
    async def _fetch(self, url: str) -> str:
        """공통 HTTP GET 요청 헬퍼"""
        session = await self._get_session()
        async with session.get(url, timeout=30) as response:
            response.raise_for_status()
            return await response.text()
    
    def _extract_year(self, text: str) -> int:
        """텍스트에서 연도 추출"""
        
        # 4자리 연도 패턴 찾기 (숫자가 아닌 문자로 둘러싸인 19xx 또는 20xx)
        # 예: "2023", "c2023", "(2023)", "2023." 등
        year_pattern = r'(?<!\d)(?:19|20)\d{2}(?!\d)'
        matches = re.findall(year_pattern, text)
        
        if matches:
            # 가장 최근 연도 반환
            return max(map(int, matches))
        
        return 0 
