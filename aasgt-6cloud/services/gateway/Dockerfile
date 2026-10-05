FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CATALOG_SERVICE_URL=http://localhost:5001
ENV ORDER_SERVICE_URL=http://localhost:5002
ENV PAYMENT_SERVICE_URL=http://localhost:5003
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "app.py"]
