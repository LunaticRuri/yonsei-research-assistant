import json
import re

# 파일 경로 설정
input_file = 'finetune_dataset.jsonl'
output_file = 'filtered_dataset.jsonl'

# 한글 포함 여부를 확인하는 정규표현식 (가-힣)
def contains_korean(text):
    korean_pattern = re.compile('[가-힣]')
    return bool(korean_pattern.search(text))

# 처리 로직
processed_count = 0
filtered_count = 0

with open(input_file, 'r', encoding='utf-8') as f_in, \
     open(output_file, 'w', encoding='utf-8') as f_out:
    
    for line in f_in:
        try:
            data = json.loads(line)
            positive_text = data.get('positive', '')
            negative_text = data.get('negative', '')
            # positive 텍스트에 한글이 포함된 경우에만 저장
            # (영어로만 적혀있다면 한글이 없으므로 제외됨)
            if contains_korean(positive_text):
                # ensure_ascii=False를 사용해야 한글이 깨지지 않고 저장됩니다.
                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
                processed_count += 1
            elif contains_korean(negative_text):
                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
                processed_count += 1
            else:
                filtered_count += 1
                
        except json.JSONDecodeError:
            print(f"JSON 형식이 잘못된 라인이 있습니다: {line[:50]}...")
            continue

print(f"작업 완료!")
print(f"- 저장된 데이터: {processed_count}건")
print(f"- 제외된 데이터(영어 등): {filtered_count}건")