FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY config ./config
COPY practice ./practice
COPY data/canonical ./data/canonical
COPY data/media ./data/media

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py import_dataset && uvicorn config.asgi:application --host 0.0.0.0 --port 8000"]
