# backend/strategy-service/app/test_routing_module.py
import asyncio
from openai import OpenAI # 실제로는 config에서 클라이언트를 가져와야 합니다.

# 2단계에서 만든 서비스 함수를 import
from app.services.routing_service import get_routing_decision 

async def main():
    # [!] 중요: 실제로는 .env와 config.py를 통해 클라이언트를 가져와야 합니다.
    #     (창현 님이 리팩토링한 LLM 클라이언트 팩토리를 사용하세요)
    try:
        client = OpenAI() 
    except Exception as e:
        print("OPENAI_API_KEY를 확인하세요.")
        return

    # --- 테스트할 질문들 ---
    queries = [
        "AI가 고용에 미치는 영향에 대한 최신 연구 논문 찾아줘", # -> rag_service 예상
        "미적분학 교재 추천해줘",                        # -> rag_service 예상
        "연세대학교 중앙도서관 위치 알려줘",                 # -> search_agent_service 예상 (학내 자료가 아님)
        "오늘 서울 날씨 어때?",                           # -> search_agent_service 예상
    ]

    print("="*30 + "\n  라우팅 모듈 테스트 시작\n" + "="*30)

    for q in queries:
        print(f"\n▶ 질문: {q}")
        decision = await get_routing_decision(q, client)
        print(f"  - 경로: {decision.route}")
        print(f"  - 이유: {decision.reason}")

    print("\n▶ 테스트 완료.")

if __name__ == "__main__":
    asyncio.run(main())