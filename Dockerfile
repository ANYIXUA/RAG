FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m pip install --upgrade pip

COPY pyproject.toml README.md ./
COPY rag_app ./rag_app

RUN python -m pip install --retries 10 --timeout 120 -e ".[commercial]"

COPY data ./data
COPY docs ./docs

RUN mkdir -p /app/storage /app/logs

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "rag_app.api:app", "--host", "0.0.0.0", "--port", "8000"]
