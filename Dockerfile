# API EGO-AI (Flask) — não sobe Streamlit
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY flask_api.py ego_supabase.py legal_copy.py ./
COPY ego_api ./ego_api

CMD sh -c 'exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 2 --timeout 180 flask_api:app'
