FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY data ./data
COPY evals ./evals
COPY ui ./ui
COPY .streamlit ./.streamlit
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./
RUN pip install .

# Bake the embedding model into the image so the first request doesn't download 80MB.
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as D; D()(['warmup'])"

EXPOSE 8000 8501
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
