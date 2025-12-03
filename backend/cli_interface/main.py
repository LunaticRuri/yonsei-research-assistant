import asyncio
import httpx
import uuid

from shared.config import Config

class ResearchAssistantCLI:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        self.client = httpx.AsyncClient(timeout=60.0)

    async def start(self):
        print("-" * 50)
        print("연세대학교 AI 수리조교 CLI에 오신 것을 환영합니다!")
        print("연구 주제나 궁금한 것에 대해 자유롭게 이야기해 주세요.")
        print("명령어 도움말이 필요하시면 '!help'를 입력하세요.")
        print("검색을 시작하려면 '!search [검색어]'를 입력하거나, 대화 중 검색 의도가 파악되면 자동으로 진행됩니다.")
        print("-" * 50)

        while True:
            try:
                user_input = input("\nUser > ").strip()
                
                if not user_input:
                    continue
                
                # 도움말 명령어 처리
                if user_input == '!help':
                    print("\n[명령어 도움말]")
                    print("!help          : 명령어 도움말 표시")
                    print("!save          : 대화 기록 저장(사용자가 복사할 수 있도록 함)")
                    print("!exit, !quit, !q : 프로그램 종료")
                    print("!new, !reset   : 새로운 세션 시작")
                    print("!search [검색어] : 즉시 검색 모드로 전환하여 검색 실행")
                    continue 
                
                # 저장 명령어 처리
                if user_input == '!save':
                    await self.save_conversation_history()
                    continue

                # 종료 명령어 처리
                if user_input.lower() in ['!exit', '!quit', '!q']:
                    print("안녕히 가세요!")
                    break
                
                # !new 또는 !reset 명령어로 새로운 세션 시작
                if user_input == '!new' or user_input == '!reset':
                    self.session_id = str(uuid.uuid4())
                    self.conversation_history = []
                    print(f"🔄 새로운 세션이 시작되었습니다. (ID: {self.session_id})")
                    continue

                # !search 명령어로 즉시 검색 모드 진입
                if user_input.startswith("!search"):
                    query = user_input.replace("!search", "").strip()
                    if not query:
                        print("검색어를 입력해 주세요.")
                        continue
                    await self.run_search_pipeline(query)
                    continue

                # 기본: Dialogue Service와 대화
                await self.process_dialogue(user_input)

            except KeyboardInterrupt:
                print("\n종료합니다.")
                break
            except Exception as e:
                print(f"\n[Error] {e}")
    
    async def save_conversation_history(self):
        """대화 기록을 화면에 출력 (사용자가 복사할 수 있도록 함)"""
        if not self.conversation_history:
            print("저장할 대화 기록이 없습니다.")
            return

        print("\n" + "="*20 + " 💾 대화 기록 저장 " + "="*20)
        print(f"Session ID: {self.session_id}\n")
        
        # 대화 내용을 보기 좋게 출력
        for line in self.conversation_history:
            print(line)
            
        print("="*58)
        print("위 내용을 복사(Cmd+C / Ctrl+C)하여 저장하세요.")
        print("="*58 + "\n")


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
            print(f"\nAI > {ai_message}")

            # 대화 기록 업데이트 (클라이언트 측에서도 유지 필요 시)
            self.conversation_history.append(f"User: {user_input}")
            self.conversation_history.append(f"AI: {ai_message}")

            # TODO: Dialogue Service가 검색이 필요하다고 판단하는 플래그를 주면 여기서 자동 검색 전환 가능
            # 현재는 !search 명령어로 수동 전환 유도

        except httpx.HTTPStatusError as e:
            print(f"[Dialogue Service Error] {e.response.status_code}: {e.response.text}")
        except Exception as e:
            print(f"[Connection Error] Dialogue Service에 연결할 수 없습니다: {e}")

    async def run_search_pipeline(self, query: str):
        """Strategy -> Retrieval -> Generation 파이프라인 실행"""
        print(f"\n🔍 '{query}'에 대한 검색 및 분석을 시작합니다...")

        try:
            # 1. Strategy Service (키워드 생성 + 검색 수행)
            print("   [1/3] 검색 전략 수립 및 데이터 수집 중...")
            strategy_payload = {
                "query": query,
                "mode": "openai" # 또는 'lora' 등 설정 가능
            }
            strategy_response = await self.client.post(
                f"{SERVICES['strategy']}/api/v1/strategy/keywords", 
                json=strategy_payload
            )
            strategy_response.raise_for_status()
            strategy_data = strategy_response.json()
            
            retrieval_result = strategy_data.get("retrieval_result")
            if not retrieval_result:
                print("   ❌ 검색 결과가 없습니다.")
                return

            # 검색 결과 요약 출력
            results = retrieval_result.get("results", [])
            print(f"   ✅ {len(results)}건의 문서를 찾았습니다.")

            # 2. Generation Service (답변 생성)
            print("   [2/3] 답변 생성 중...")
            generation_payload = {
                "query": query,
                "retrieval_result": retrieval_result
            }
            
            # Generation Service 호출
            gen_response = await self.client.post(
                f"{SERVICES['generation']}/generate",
                json=generation_payload
            )
            gen_response.raise_for_status()
            gen_data = gen_response.json()

            # 3. 최종 결과 출력
            print("\n" + "="*20 + " 📝 최종 답변 " + "="*20)
            print(gen_data.get("answer", "답변을 생성할 수 없습니다."))
            print("="*50)
            
            # 참고 문헌 출력 (있다면)
            # print("\n[참고 문헌]")
            # ...

        except httpx.HTTPStatusError as e:
            print(f"[Service Error] {e.response.status_code}: {e.response.text}")
        except Exception as e:
            print(f"[Pipeline Error] 처리 중 오류가 발생했습니다: {e}")

async def main():
    cli = ResearchAssistantCLI()
    await cli.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
