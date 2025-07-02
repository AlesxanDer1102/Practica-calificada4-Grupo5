
FROM python:3.10-slim

WORKDIR /app

# Install necessary dependencies for psycopg2
RUN apt-get update && apt-get install -y gcc libpq-dev openssl && rm -rf /var/lib/apt/lists/*

COPY app/ ./
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "app.py"]
