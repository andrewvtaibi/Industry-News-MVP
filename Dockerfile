# Dockerfile for the Industry News webapp
# Build: docker build -t industry-news .
# Run:   docker run -p 8000:8000 industry-news

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app/        ./app/
COPY server/     ./server/
COPY static/     ./static/
COPY data/       ./data/

EXPOSE 8000

# Use 2 workers for cloud; adjust via WORKERS env var
CMD ["sh", "-c", \
  "uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2}"]
