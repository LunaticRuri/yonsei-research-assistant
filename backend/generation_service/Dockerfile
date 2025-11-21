# 📍 수정할 파일: backend/rag-service/Dockerfile

FROM python:3.11-slim

WORKDIR /app/backend
ENV PYTHONPATH "${PYTHONPATH}:/app/backend"

COPY ./rag-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./rag-service /app/backend/rag-service
COPY ./shared /app/backend/shared

WORKDIR /app/backend/rag-service

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]