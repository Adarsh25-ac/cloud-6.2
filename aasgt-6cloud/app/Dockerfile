FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Environment defaults (override with -e DB_HOST=<VM2_INTERNAL_IP> at runtime)
ENV DB_HOST=localhost
ENV DB_PORT=5432
ENV DB_NAME=recipedb
ENV DB_USER=recipeuser
ENV DB_PASSWORD=recipepassword
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Run with Gunicorn production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--timeout", "60", "app:app"]
