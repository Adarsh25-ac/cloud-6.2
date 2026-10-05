FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DB_PATH=/data/payments.db
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /data

EXPOSE 5003

CMD ["python", "app.py"]
