FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DB_PATH=/data/orders.db
ENV CATALOG_SERVICE_URL=http://localhost:5001
ENV PAYMENT_SERVICE_URL=http://localhost:5003
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /data

EXPOSE 5002

CMD ["python", "app.py"]
