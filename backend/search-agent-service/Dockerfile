# 📍 수정할 파일: backend/search-agent-service/Dockerfile

FROM python:3.11-slim

WORKDIR /app/backend
ENV PYTHONPATH "${PYTHONPATH}:/app/backend"

COPY ./search-agent-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./search-agent-service /app/backend/search-agent-service
COPY ./shared /app/backend/shared

WORKDIR /app/backend/search-agent-service

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]