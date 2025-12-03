# Prompts for Self-RAG evaluation

SELF_RAG_RELEVANCE_PROMPT_TEMPLATE = """
사용자 질문: {query_text}
검색된 문서:
{documents_text}
위 문서들은 사용자 질문에 따라 검색된 책 또는 논문들의 소개, 요약 문서들이다.
이 문서들이 소개하고 있는 자료들이 전반적으로 사용자 질문과 얼마나 관련이 있는지 1에서 5까지의 척도로 평가하라. (evaluation)
문서 텍스트 내용 자체가 아니라 문서들이 소개하는 자료가 질문과 관련이 있는지를 추론하여 평가하는 것이다.
1은 전혀 관련이 없음, 5는 매우 관련이 있음이다.
판단한 이유도 간단히 설명하라. (reason)
"""

SELF_RAG_HALLUCINATION_PROMPT_TEMPLATE = """
생성된 답변:
{answer_text}
검색된 문서:
{documents_text}
위 문서들은 사용자 질문에 따라 검색된 책 또는 논문들의 소개, 요약 문서들이다.
생성된 답변이 위 문서들에 근거하여 생성되었는지 1에서 5까지의 척도로 평가하라. (evaluation)
1은 전혀 근거 없음, 5는 매우 근거에 기반함.
판단한 이유도 간단히 설명하라. (reason)
"""

SELF_RAG_HELPFULNESS_PROMPT_TEMPLATE = """
사용자 질문: {query_text}
생성된 답변:
{answer_text}
생성된 답변이 사용자 질문에 얼마나 도움이 되는지 1에서 5까지의 척도로 평가하라. (evaluation)
1은 전혀 도움이 되지 않음, 5는 매우 도움이 됨입니다.
판단한 이유도 간단히 설명하라. (reason)
"""

# TODO: 최종 답변 생성 프롬프트 개선 필요
FINAL_GENERATION_PROMPT_TEMPLATE = """
당신은 연세대학교 사서 AI 입니다. 다음 정보는 사용자 질문에 대해 검색된 책 또는 논문들의 소개, 요약 문서들입니다.

사용자 질문: {query_text}
검색된 문서:
{documents_text}

이를 바탕으로 사용자 질문에 최적의 답변을 생성하세요.
이떄 답변은 질문에 대한 직접적인 답변이 아니고, 검색된 자료들이 질문에 어떻게 도움이 되는지 소개하는 형식이어야 합니다.
답변은 한국어로 작성하세요.
"""