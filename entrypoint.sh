#!/bin/bash
set -e

# Write environment variables to a file for cron
printenv | grep -E '^(BROKER|BROKERPORT|USERNAME|PASSWORD|DEVICE_TOPIC|TIMER_SECONDS)=' > /app/.env

# Ensure cron log file exists before the first run.
touch /var/log/cron.log

# Setup cron job (every 15 minutes)
# Keep only the most recent 1000 lines to prevent unbounded growth.
echo "*/15 * * * * cd /app && export \$(cat /app/.env | xargs) && /usr/local/bin/python3 /app/ping.py >> /var/log/cron.log 2>&1; tail -n 1000 /var/log/cron.log > /var/log/cron.log.tmp && mv /var/log/cron.log.tmp /var/log/cron.log" | crontab -

# Start cron in background
cron

echo "Starting router watchdog..."
echo "  - Cron job: every 15 minutes"
echo "  - Monitor: listening for power events"
echo "  - Web UI: http://0.0.0.0:5000"

# Start web UI in background
python3 /app/web.py &

# Run monitor in foreground
exec python3 /app/monitor.py
