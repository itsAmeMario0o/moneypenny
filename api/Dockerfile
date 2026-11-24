FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Trust any extra certificate authorities in api/certs/ (see the README there).
# httpx (used by the Anthropic SDK) and requests read these two variables.
RUN cp /app/certs/*.crt /usr/local/share/ca-certificates/ 2>/dev/null; update-ca-certificates
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV TRADINGAGENTS_RESULTS_DIR=/data/tradingagents/logs \
    TRADINGAGENTS_CACHE_DIR=/data/tradingagents/cache \
    TRADINGAGENTS_MEMORY_LOG_PATH=/data/tradingagents/memory/trading_memory.md \
    TRADINGAGENTS_NO_UPDATE_CHECK=1
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
