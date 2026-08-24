# Backend image — Flask API.  (PROTOTYPE: runs the Flask dev server; no Gunicorn/Nginx yet.)
FROM python:3.12-slim

# libmagic1 -> python-magic (MIME sniffing).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# For the prototype we run migrations then the dev server.
# (Production will use an entrypoint that waits for the DB and runs Gunicorn.)
ENV FLASK_APP=wsgi:app
EXPOSE 5000
CMD ["sh", "-c", "flask db upgrade && flask run --host=0.0.0.0 --port=5000"]
