# 1. 베이스 이미지 설정
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 소스 코드 복사
COPY . .

# 5. 포트 노출 (이 부분은 서비스마다 달라도 되지만, uvicorn에서 지정하므로 통일해도 괜찮습니다)
EXPOSE 8000

# --- [추가] 파이썬이 모듈을 찾을 기준 경로를 설정합니다. ---
ENV PYTHONPATH "${PYTHONPATH}:/app"
# ---------------------------------------------------

# 6. 서버 실행 명령어
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]