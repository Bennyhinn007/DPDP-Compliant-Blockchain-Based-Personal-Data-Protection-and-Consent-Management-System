FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create keystore directory
RUN mkdir -p /app/keystore

EXPOSE 5000

# Production WSGI server. PORT is provided by the host (defaults to 5000).
ENV PORT=5000
CMD ["sh", "-c", "gunicorn run:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
