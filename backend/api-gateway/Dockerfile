# 📍 수정할 파일: backend/api-gateway/Dockerfile

FROM python:3.11-slim

WORKDIR /app/backend
ENV PYTHONPATH "${PYTHONPATH}:/app/backend"

COPY ./api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./api-gateway /app/backend/api-gateway
COPY ./shared /app/backend/shared

WORKDIR /app/backend/api-gateway

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]