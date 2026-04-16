FROM python:3.11-slim

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN uv sync --no-dev

COPY . /app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
