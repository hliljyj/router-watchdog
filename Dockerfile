FROM python:3.12-slim

WORKDIR /app

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY config.py .
COPY reset_timer.py .
COPY seed_rule.py .
COPY monitor.py .
COPY web.py .
COPY entrypoint.sh .

EXPOSE 5000

RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
