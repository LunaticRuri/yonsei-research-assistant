# 📍 수정할 파일: backend/dialogue-service/Dockerfile

FROM python:3.11-slim

WORKDIR /app/backend
ENV PYTHONPATH "${PYTHONPATH}:/app/backend"

COPY ./dialogue-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./dialogue-service /app/backend/dialogue-service
COPY ./shared /app/backend/shared

WORKDIR /app/backend/dialogue-service

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]