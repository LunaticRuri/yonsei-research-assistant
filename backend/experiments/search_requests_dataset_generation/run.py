import os
import json
import asyncio
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

from shared.models import SearchRequest, SearchQueries, RetrievalRoute, LibrarySearchField, ElectronicSearchField, QueryOperator

# KDC 100 Divisions
KDC_DIVISIONS = {
    "000": "총류", "010": "도서학, 서지학", "020": "문헌정보학", "030": "백과사전", "040": "강연집, 수필집, 연설문집",
    "050": "일반연속간행물", "060": "일반 학회, 단체, 협회, 기관, 연구기관", "070": "신문, 저널리즘", "080": "일반 전집, 총서", "090": "향토자료",
    "100": "철학", "110": "형이상학", "120": "인식론, 인과론, 인간학", "130": "철학의 체계", "140": "경학",
    "150": "동양철학, 동양사상", "160": "서양철학", "170": "논리학", "180": "심리학", "190": "윤리학, 도덕철학",
    "200": "종교", "210": "비교종교", "220": "불교", "230": "기독교", "240": "도교",
    "250": "천도교", "260": "[미사용]", "270": "힌두교, 브라만교", "280": "이슬람교(회교)", "290": "기타 제종교",
    "300": "사회과학", "310": "통계자료", "320": "경제학", "330": "사회학, 사회문제", "340": "정치학",
    "350": "행정학", "360": "법률, 법학", "370": "교육학", "380": "풍습, 예절, 민속학", "390": "국방, 군사학",
    "400": "자연과학", "410": "수학", "420": "물리학", "430": "화학", "440": "천문학",
    "450": "지학", "460": "광물학", "470": "생명과학", "480": "식물학", "490": "동물학",
    "500": "기술과학", "510": "의학", "520": "농업, 농학", "530": "공학, 공업일반, 토목공학, 환경공학", "540": "건축, 건축학",
    "550": "기계공학", "560": "전기공학, 통신공학, 전자공학", "570": "화학공학", "580": "제조업", "590": "생활과학",
    "600": "예술", "610": "[미사용]", "620": "조각, 조형미술", "630": "공예", "640": "서예",
    "650": "회화, 도화, 디자인", "660": "사진예술", "670": "음악", "680": "공연예술, 매체예술", "690": "오락, 스포츠",
    "700": "언어", "710": "한국어", "720": "중국어", "730": "일본어 및 기타 아시아 제어", "740": "영어",
    "750": "독일어", "760": "프랑스어", "770": "스페인어 및 포르투갈어", "780": "이탈리아어", "790": "기타 제어",
    "800": "문학", "810": "한국문학", "820": "중국문학", "830": "일본문학 및 기타 아시아 제문학", "840": "영미문학",
    "850": "독일문학", "860": "프랑스 문학", "870": "스페인 및 포르투갈 문학", "880": "이탈리아 문학", "890": "기타 제문학",
    "900": "역사", "910": "아시아", "920": "유럽", "930": "아프리카", "940": "북아메리카",
    "950": "남아메리카", "960": "오세아니아, 양극지방", "970": "[미사용]", "980": "지리", "990": "전기"
}
EXCLUDE_KDC_CODES = {"030", "040", "050", "060", "080", "990"}

# Pydantic model for Gemini response
class GeneratedQuestion(BaseModel):
    question: str
    keywords: List[str]

async def generate_dataset():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        return

    client = genai.Client(api_key=api_key)
    
    dataset = []
    
    print(f"Starting generation for {len(KDC_DIVISIONS)} KDC divisions...")

    for code, name in KDC_DIVISIONS.items():
        if code in EXCLUDE_KDC_CODES:
            continue
        if name == "[미사용]":
            continue
        # NOTE: 논문 부분 테스트 할 때는 books_prompt 대신 electronics_prompt 사용
        electronics_prompt = f"""
        KDC (Korean Decimal Classification) 주제 '{code} {name}'에 해당하는 분야에 대한 궁금증이 드러나는 학문적 질문 하나와 그 질문에서 추출할 수 있는 검색 키워드들을 생성해.
        
        예시:
        주제: 360 법률, 법학
        질문: "민법상 불법행위 책임(제750조) 성립 요건 중 위법성의 판단 기준을 어떻게 해석해야 하는가?"
        키워드: ["불법행위 책임 요건", "위법성 판단 기준"]
        
        주의사항!
        1. 질문은 하나의 질문 내용만 담고 있어야 해. 아래는 각각 잘못된 예시와 올바른 예시야.
        잘못된 예시:
            기후 변화가 특정 지역의 식생 분포에 미치는 영향은 무엇이며, 이를 연구하는 주요 방법론은 어떤 것들이 있는가?
            블랙홀은 어떻게 형성되며, 그 특성은 무엇인가?
            -> 2개의 질문 내용을 담고 있어서 안됨.
        올바른 예시:
            기후 변화가 아열대 지역의 식생 분포에 미치는 주요 영향은 무엇인가?
            인간의 자유의지는 인과론적 결정론과 양립할 수 있는가, 아니면 본질적으로 충돌하는 개념인가?
            -> 하나의 질문 내용만 담고 있어서 됨.
        
        2. 검색 키워드는 최소 1개, 그리고 3개 까지 생성 가능. 각 키워드가 서로 중복된 내용을 담으면 안됨.
        질문: "천도교의 핵심 교리인 '인내천(人乃天)' 사상이 현대 사회에 어떤 의미를 가지는가?" 인 경우
        잘못된 예시:
            키워드: ["천도교 교리", "인내천 사상", "천도교 인내천"]
            -> 키워드가 중복된 내용을 담고 있어서 안됨.
        올바른 예시:
            키워드: ["천도교 인내천", "현대 사회"]

        3. 키워드는 되도록이면 2개 이하 단어, 검색어가 너무 길거나 복잡하면 안됨.

        4. 최대한 명확하고 간단한 키워드로 생성. 질문을 반복하는 키워드보다는 질문을 해결하는 자료(특히 논문, 학술지)를 찾게 도와주는 키워드가 좋다.
                    
        위 예시와 같은 형식으로 JSON 객체를 생성해.
        """
        
        books_prompt = f"""
        KDC (Korean Decimal Classification) 주제 '{code} {name}'에 해당하는 분야에 대한 일반적인 질문 하나와 그 질문에서 추출할 수 있는 검색 키워드들을 생성해.
        예시:
        주제: 320 경제학
        질문: "인플레이션이 국가 경제에 미치는 주요 영향은 무엇인가?"
        키워드: ["인플레이션 영향", "국가 경제"]
        주의사항!
        1. 질문은 하나의 질문 내용만 담고 있어야 해. 아래는 각각 잘못된 예시와 올바른 예시야.
        잘못된 예시:
            기후 변화가 국가 경제에 영향은 무엇이며, 이를 연구하는 주요 방법론은 어떤 것들이 있는가?
            블랙홀은 어떻게 형성되며, 그 특성은 무엇인가?
            -> 2개의 질문 내용을 담고 있어서 안됨.
        올바른 예시:
            기후 변화가 국가 경제에 미치는 주요 영향은?
            블랙홀의 어떻게 형성되는가?
            -> 하나의 질문 내용만 담고 있어서 됨.
        2. 검색 키워드는 최소 1개, 그리고 3개 까지 생성 가능. 각 키워드가 서로 중복된 내용을 담으면 안됨.
        질문: "천도교의 핵심 교리인 '인내천(人乃天)' 사상은 무엇인가" 인 경우
        잘못된 예시:
            키워드: ["천도교 교리", "인내천 사상", "천도교 인내천"]
            -> 키워드가 중복된 내용을 담고 있어서 안됨.
        올바른 예시:
            키워드: ["천도교", "인내천"]
            -> 키워드가 중복된 내용을 담고 있지 않아서 됨.
        3. 키워드는 되도록이면 2개 이하 단어, 검색어가 너무 길거나 복잡하면 안됨.
        4. 최대한 명확하고 간단한 키워드로 생성. 질문을 반복하는 키워드보다는 질문을 해결하는 자료(책, 단행본)를 찾게 도와주는 키워드가 좋다.
        """

        prompt = books_prompt

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                    response_schema=GeneratedQuestion
                )
            )
            
            if response.text:
                data = json.loads(response.text)
                generated_q = GeneratedQuestion(**data)
                
                # Convert to SearchRequest
                keywords = generated_q.keywords
                
                # Initialize with first keyword
                search_queries_args = {
                    "query_1": keywords[0] if keywords else "",
                    "search_field_1": "TOTAL"
                }
                
                # Add second keyword if exists
                if len(keywords) > 1:
                    search_queries_args["query_2"] = keywords[1]
                    search_queries_args["search_field_2"] = "TOTAL"
                    search_queries_args["operator_1"] = QueryOperator.AND
                    
                # Add third keyword if exists
                if len(keywords) > 2:
                    search_queries_args["query_3"] = keywords[2]
                    search_queries_args["search_field_3"] = "TOTAL"
                    search_queries_args["operator_2"] = QueryOperator.AND
                
                search_queries = SearchQueries(**search_queries_args)
                
                search_request = SearchRequest(
                    queries=search_queries,
                    routes=[RetrievalRoute.VECTOR_DB],
                    top_k=10,
                    user_query=generated_q.question
                )
                
                print(f"Generated for {code} {name}: Question: {generated_q.question}, Keywords: {keywords}")

                dataset.append(search_request.model_dump(mode='json'))
                print(f"Generated for {code} {name}")
                
        except Exception as e:
            print(f"Error generating for {code} {name}: {e}")
            # Continue to next
            continue

    # Save to file
    output_file = os.path.join(os.path.dirname(__file__), 'generated_search_requests.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"Dataset generation complete. Saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(generate_dataset())
