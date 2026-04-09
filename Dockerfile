FROM python:3.12-slim

WORKDIR /app

# Install cron and curl (for health check)
RUN apt-get update && apt-get install -y cron curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY config.py .
COPY ping.py .
COPY seed_rule.py .
COPY monitor.py .
COPY web.py .
COPY entrypoint.sh .

EXPOSE 5000

RUN chmod +x entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/healthz || exit 1

CMD ["./entrypoint.sh"]
