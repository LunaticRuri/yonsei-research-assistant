import os
import sys
import json
import asyncio
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

# Add project root to sys.path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.shared.models import SearchRequest, SearchQueries, RetrievalRoute, LibrarySearchField, ElectronicSearchField, QueryOperator

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
        if name == "[미사용]":
            continue
            
        prompt = f"""
        KDC (Korean Decimal Classification) 주제 '{code} {name}'에 해당하는 분야에 대해 궁금증이나 학문적 내용이 드러나는 질문 하나와 그 질문에서 추출할 수 있는 검색 키워드들을 생성해주세요.
        
        예시:
        주제: 365 민법
        질문: "민법상 불법행위 책임(제750조) 성립 요건 중 위법성의 판단 기준을 어떻게 해석해야 하는가? 특히, 영업 방해나 명예 훼손과 같은 무형적 손해에 대한 위법성 조각 사유(예: 정당행위)의 구체적인 적용 범위는 무엇인가?"
        키워드: ["불법행위 책임 요건", "위법성 판단 기준", "위법성 조각 사유", "영업 방해", "명예 훼손", "정당행위"]
        
        위 예시와 같은 형식으로 JSON 객체를 생성해주세요.
        """

        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash', # Or gemini-1.5-pro, using a likely available model
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
                # Join keywords with spaces if 3 or more, as per instruction
                # "이때 키워드가 3개 이상이면 한 쿼리에 띄어쓰기로 구분하여 이어 쓸수도 있음"
                # We will join them all into query_1 for simplicity and effectiveness in vector search
                query_str = " ".join(generated_q.keywords)
                
                search_queries = SearchQueries(
                    query_1=query_str,
                    search_field_1="TOTAL" # Default to TOTAL
                )
                
                search_request = SearchRequest(
                    queries=search_queries,
                    routes=[RetrievalRoute.VECTOR_DB, RetrievalRoute.YONSEI_HOLDINGS, RetrievalRoute.YONSEI_ELECTRONICS]
                )
                
                # We might want to store the original question too, but SearchRequest doesn't have it.
                # For the purpose of the dataset file, maybe we can wrap it or just dump the SearchRequest.
                # The user said "SearchRequest 모델 규격에 맞추어 생성하면 된다".
                # So we will append the SearchRequest dict.
                
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
