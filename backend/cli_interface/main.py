import asyncio
import httpx
import uuid
import sys

from shared.config import settings

# 서비스 URL 정의
SERVICES = {
    "dialogue": settings.DIALOGUE_SERVICE_URL,
    "strategy": settings.STRATEGY_SERVICE_URL,
    "retrieval": settings.RETRIEVAL_SERVICE_URL,
    "generation": settings.GENERATION_SERVICE_URL,
}

class ResearchAssistantCLI:
    def __init__(self, reader, writer):
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        self.client = httpx.AsyncClient(timeout=180.0)
        self.reader = reader
        self.writer = writer

    async def print(self, message: str = ""):
        """클라이언트에게 메시지 전송"""
        try:
            self.writer.write((str(message) + "\n").encode('utf-8'))
            await self.writer.drain()
        except Exception:
            pass

    async def input(self, prompt: str = "") -> str:
        """클라이언트로부터 입력 받기"""
        try:
            if prompt:
                self.writer.write(prompt.encode('utf-8'))
                await self.writer.drain()
            
            line = await self.reader.readline()
            if not line:
                raise ConnectionResetError("Connection closed by client")
            return line.decode('utf-8').strip()
        except Exception as e:
            raise e

    async def start(self):
        try:
            await self.print("-" * 50)
            await self.print("연세대학교 AI 수리조교 CLI에 오신 것을 환영합니다!")
            await self.print("연구 주제나 궁금한 것에 대해 자유롭게 이야기해 주세요.")
            await self.print("명령어 도움말이 필요하시면 '!help'를 입력하세요.")
            await self.print("검색을 시작하려면 '!search [검색 질문]'를 입력하세요.")
            await self.print("또는 대화 중 검색 의도가 파악되면 자동으로 진행됩니다. (기능 구현 중!)")
            await self.print("-" * 50)

            while True:
                try:
                    user_input = await self.input("\nUser > ")
                    
                    if not user_input:
                        continue
                    
                    # 도움말 명령어 처리
                    if user_input == '!help':
                        await self.print("\n[명령어 도움말]")
                        await self.print("!help          : 명령어 도움말 표시")
                        await self.print("!save          : 대화 기록 저장(사용자가 복사할 수 있도록 함)")
                        await self.print("!exit, !quit, !q : 프로그램 종료")
                        await self.print("!new, !reset   : 새로운 세션 시작")
                        await self.print("!search [검색어] : 즉시 검색 모드로 전환하여 검색 실행 (예: !search 조선 후기 농민의 생활상을 알고 싶다.)")
                        continue 
                    
                    # 저장 명령어 처리
                    if user_input == '!save':
                        await self.save_conversation_history()
                        continue

                    # 종료 명령어 처리
                    if user_input.lower() in ['!exit', '!quit', '!q']:
                        await self.print("안녕히 가세요!")
                        break
                    
                    # !new 또는 !reset 명령어로 새로운 세션 시작
                    if user_input == '!new' or user_input == '!reset':
                        self.session_id = str(uuid.uuid4())
                        self.conversation_history = []
                        await self.print(f"🔄 새로운 세션이 시작되었습니다. (ID: {self.session_id})")
                        continue

                    # !search 명령어로 즉시 검색 모드 진입
                    if user_input.startswith("!search"):
                        query = user_input.replace("!search", "").strip()
                        if not query:
                            await self.print("검색어를 입력해 주세요.")
                            continue
                        await self.run_search_pipeline(query)
                        continue

                    # 기본: Dialogue Service와 대화
                    # FIXME: 대화 중 검색 의도가 파악되면 자동으로 검색 모드로 전환하는 기능 구현 필요
                    # await self.process_dialogue(user_input)

                except ConnectionResetError:
                    break
                except Exception as e:
                    await self.print(f"\n[Error] {e}")
        finally:
            await self.client.aclose()
            self.writer.close()
            await self.writer.wait_closed()
    
    async def save_conversation_history(self):
        """대화 기록을 화면에 출력 (사용자가 복사할 수 있도록 함)"""
        if not self.conversation_history:
            await self.print("저장할 대화 기록이 없습니다.")
            return

        await self.print("\n" + "="*20 + " 대화 기록 저장 " + "="*20)
        await self.print(f"Session ID: {self.session_id}\n")
        
        # 대화 내용을 보기 좋게 출력
        for line in self.conversation_history:
            await self.print(line)
            
        await self.print("="*58)
        await self.print("위 내용을 복사하여 저장하세요.")
        await self.print("="*58 + "\n")


    async def process_dialogue(self, user_input: str):
        """Dialogue Service와 통신"""
        try:
            payload = {
                "session_id": self.session_id,
                "message": user_input,
                "conversation_history": self.conversation_history
            }
            
            response = await self.client.post(f"{SERVICES['dialogue']}/dialogue", json=payload)
            response.raise_for_status()
            data = response.json()

            # 응답 출력
            ai_message = data.get("response_text", "")
            await self.print(f"\nAI > {ai_message}")

            # 대화 기록 업데이트 (클라이언트 측에서도 유지 필요 시)
            self.conversation_history.append(f"User: {user_input}")
            self.conversation_history.append(f"AI: {ai_message}")

            # TODO: Dialogue Service가 검색이 필요하다고 판단하는 플래그를 주면 여기서 자동 검색 전환 가능
            # 현재는 !search 명령어로 수동 전환 유도

        except httpx.HTTPStatusError as e:
            await self.print(f"[Dialogue Service Error] {e.response.status_code}: {e.response.text}")
        except Exception as e:
            await self.print(f"[Connection Error] Dialogue Service에 연결할 수 없습니다: {e}")

    async def run_search_pipeline(self, query: str):
        """Strategy -> Retrieval -> Generation 파이프라인 실행"""
        await self.print(f"\n🔍 '{query}'에 대한 검색 및 분석을 시작합니다...")

        try:
            # 1. Strategy Service (키워드 생성 + 검색 수행)
            await self.print("   [1/3] 검색 전략 수립 및 데이터 수집 중...")
            
            # NOTE: 여기서 'gemini' or 'Lora' 모드 선택 가능
            strategy_payload = {
                "query": query,
                "mode": "gemini" # 또는 'lora' 등 설정 가능
            }
            strategy_response = await self.client.post(
                f"{SERVICES['strategy']}/cli_stratrgy_request", 
                json=strategy_payload
            )
            strategy_response.raise_for_status()
            search_request = strategy_response.json()
            
            retrieval_response = await self.client.post(
                f"{SERVICES['retrieval']}/search",
                json=search_request
            )
            retrieval_response.raise_for_status()
            generation_request = retrieval_response.json()

            if not generation_request:
                await self.print("   ❌ 검색 결과가 없습니다.")
                return

            # 검색 결과 요약 출력
            results = generation_request.get("retrieval_result", []).get("documents", [])
            await self.print(f"   ✅ {len(results)}건의 문서를 찾았습니다.")

            # 3. Generation Service (답변 생성)
            await self.print("   [2/3] 답변 생성 중...")
            generation_payload = {
                "query": query,
                "retrieval_result": generation_request.get("retrieval_result", [])
            }
            
            # Generation Service 호출
            generation_response = await self.client.post(
                f"{SERVICES['generation']}/generate",
                json=generation_payload
            )
            generation_response.raise_for_status()
            final_output = generation_response.json()

            # 4. 최종 결과 출력
            await self.print("\n" + "="*20 + " 📝 최종 답변 " + "="*20)
            await self.print(final_output.get("answer", "답변을 생성할 수 없습니다."))
            await self.print("="*50)

        except httpx.HTTPStatusError as e:
            await self.print(f"[Service Error] {e.response.status_code}: {e.response.text}")
        except Exception as e:
            await self.print(f"[Pipeline Error] 처리 중 오류가 발생했습니다: {e}")

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr}")
    cli = ResearchAssistantCLI(reader, writer)
    await cli.start()
    print(f"Connection closed from {addr}")

async def main():
    server = await asyncio.start_server(
        handle_client, '0.0.0.0', settings.CLI_SERVICE_PORT)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
