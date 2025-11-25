import json
import re
import os
import glob
import multiprocessing
import time
from dotenv import load_dotenv
load_dotenv()

from google import genai

from tqdm import tqdm

# 설정
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(CURRENT_DIR, 'raw_data')
OUTPUT_DIR = os.path.join(CURRENT_DIR, 'processed_data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

INTERMEDIATE_PAIRS_FILE = os.path.join(OUTPUT_DIR, 'intermediate_pairs.jsonl')
ID_TO_ABSTRACT_FILE = os.path.join(OUTPUT_DIR, 'id_to_abstract.json')
FINAL_OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'finetune_dataset.jsonl')

# Gemini 설정 (API Key가 있을 경우에만)

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

def extract_abstract(context):
    # '초록' 또는 'Abstract' 키워드 뒤의 내용을 추출하는 간단한 로직
    # 실제 데이터 패턴에 따라 정규식 조정 필요
    pattern = r"(초록|Abstract)\s*\n(.*?)\n(핵심 어휘|Keywords|본문|서론)"
    match = re.search(pattern, context, re.DOTALL)
    if match:
        result = match.group(2).strip()
        if '\n\n' in result:
            result = result.split('\n\n')[0].strip()
        return result
    # 초록 추출 실패 시 context의 앞부분 500자 사용 (Fallback)
    return context[:500]

def load_or_create_corpus():
    """
    1차 처리: Raw 데이터를 읽어서 (Query, Positive, DocID) 쌍을 중간 파일에 저장합니다.
    이미 처리된 파일이 있으면 생략합니다.
    """
    if os.path.exists(INTERMEDIATE_PAIRS_FILE):
        print(f"기존 중간 데이터 발견: {INTERMEDIATE_PAIRS_FILE}")
        return

    print("Raw 데이터 처리를 시작합니다...")
    # glob을 사용하여 파일 목록을 가져옵니다 (메모리 효율적)
    json_files = glob.glob(os.path.join(RAW_DATA_DIR, '*.json'))
    print(f"발견된 파일 수: {len(json_files)}")
    
    id_to_abstract = {}
    
    # 중간 결과를 파일에 즉시 기록 (메모리 절약)
    with open(INTERMEDIATE_PAIRS_FILE, 'w', encoding='utf-8') as out_f:
        for file_path in tqdm(json_files, desc="1차 처리(Pairs 생성)"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # 파일 하나에 여러 논문이 있을 수도, 하나만 있을 수도 있음
                    content = json.load(f)
                    papers = content if isinstance(content, list) else [content]
                
                for paper in papers:
                    process_single_paper(paper, id_to_abstract, out_f)
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

    # id_to_abstract 저장 (필요시 사용)
    print("id_to_abstract 매핑 저장 중...")
    with open(ID_TO_ABSTRACT_FILE, 'w', encoding='utf-8') as f:
        json.dump(id_to_abstract, f, ensure_ascii=False, indent=2)

def process_single_paper(paper, id_to_abstract, out_f):
    doc_id = paper.get('doc_id')
    context = paper.get('context', '')
    
    if not doc_id or not context:
        return

    abstract = extract_abstract(context)
    if len(abstract) < 50: 
        return # 초록이 너무 짧으면 패스

    # 메모리에 ID -> Abstract 매핑 유지
    id_to_abstract[doc_id] = abstract
    
    # Query 생성 및 파일 기록
    pairs = []
    
    # A. 기존 QA 질문 활용
    for qa in paper.get('qas', []):
        pairs.append({
            "query": qa['question'],
            "positive": abstract,
            "doc_id": doc_id
        })

    # B. 논문 제목 활용
    if 'title' in paper:
        pairs.append({
            "query": paper['title'],
            "positive": abstract,
            "doc_id": doc_id
        })
    
    # C. 키워드 합성
    if 'keywords' in paper and 'ko' in paper['keywords']:
        keywords = paper['keywords']['ko'].replace(';', ' ')
        synthetic_query = f"{keywords} 관련 연구 논문이나 자료"
        pairs.append({
            "query": synthetic_query,
            "positive": abstract,
            "doc_id": doc_id
        })
        
    # JSONL 형식으로 즉시 저장
    for pair in pairs:
        out_f.write(json.dumps(pair, ensure_ascii=False) + '\n')

def generate_hard_negative(query, positive):
    """Gemini를 사용하여 Hard Negative 생성"""
    try:
        prompt = f"""
        You are an expert in generating training data for Information Retrieval.
        Given the following Query and Positive Passage, generate a "Hard Negative" passage in Korean.
        
        A Hard Negative passage should:
        1. Be on the same topic as the query and share similar keywords.
        2. But NOT answer the query or contain the specific information requested.
        3. Be plausible but incorrect or irrelevant to the specific question.
        4. Be similar in length and style to the Positive Passage.
        5. Output ONLY the generated passage text, no other commentary.

        Query: {query}
        Positive Passage: {positive}

        Hard Negative Passage:
        """
        response = response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
        return response.text.strip()
    except Exception as e:
        # Rate limit이나 기타 오류 발생 시 None 반환
        return None

def process_line_batch(lines):
    """여러 라인을 한 번에 처리하여 결과를 반환하는 함수"""
    results = []
    for line in lines:
        try:
            pair = json.loads(line)
            query = pair['query']
            positive_abstract = pair['positive']
            
            # Gemini를 이용해 Hard Negative 생성
            # API 호출이므로 너무 빠른 속도로 요청하면 Rate Limit에 걸릴 수 있음
            time.sleep(0.5)  # 간단한 속도 제한
            negative_abstract = generate_hard_negative(query, positive_abstract)
            
            if negative_abstract:
                output_entry = {
                    "query": query,
                    "positive": positive_abstract,
                    "negative": negative_abstract
                }
                results.append(json.dumps(output_entry, ensure_ascii=False))
            else:
                # 생성 실패 시 해당 데이터는 건너뜀
                pass
                
        except Exception as e:
            continue
    return results

def batch_generator(iterable, batch_size=10):
    """데이터를 batch_size만큼 묶어서 반환"""
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch

def main():
    # 1. 데이터 준비 (이미 생성된 파일이 있으면 로드 과정 생략)
    load_or_create_corpus()
    
    # 2. Gemini 기반 데이터 생성 (이어하기 기능 지원)
    processed_count = 0
    if os.path.exists(FINAL_OUTPUT_FILE):
        with open(FINAL_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            processed_count = sum(1 for _ in f)
        print(f"이미 처리된 데이터 {processed_count} 라인을 고려하여 작업을 이어갑니다.")
    
    print("Gemini를 이용한 Hard Negative 생성 시작...")
    
    # API 호출이 주된 작업이므로 프로세스 수를 너무 많이 늘리면 Rate Limit에 걸릴 수 있음
    # 적절한 수로 조절 필요 (예: 4~8)
    num_workers = 4
    print(f"사용할 프로세스 수: {num_workers}")

    with open(INTERMEDIATE_PAIRS_FILE, 'r', encoding='utf-8') as in_f, \
         open(FINAL_OUTPUT_FILE, 'a', encoding='utf-8') as out_f:
        
        # 이미 처리한 만큼 스킵
        if processed_count > 0:
            print(f"약 {processed_count}개의 입력 쿼리를 건너뜁니다.")
            for _ in range(processed_count):
                next(in_f, None)

        # API 호출은 느리므로 배치를 작게 잡거나, 적절히 조절
        batch_size = 5
        batches = batch_generator(in_f, batch_size)
        
        with multiprocessing.Pool(processes=num_workers) as pool:
            for batch_results in tqdm(pool.imap(process_line_batch, batches), desc="Generating Data"):
                for res_line in batch_results:
                    out_f.write(res_line + '\n')
                    out_f.flush() # 실시간 저장

    print(f"모든 작업 완료. 결과 파일: {FINAL_OUTPUT_FILE}")

if __name__ == "__main__":
    main()
