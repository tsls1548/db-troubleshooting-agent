FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY db.py agent.py main.py ./

CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}