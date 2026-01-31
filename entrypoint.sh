#!/bin/bash
set -e

# Write environment variables to a file for cron
printenv | grep -E '^(BROKER|BROKERPORT|USERNAME|PASSWORD|DEVICE_TOPIC|TIMER_SECONDS)=' > /app/.env

# Setup cron job (every 15 minutes)
echo "*/15 * * * * cd /app && export \$(cat /app/.env | xargs) && /usr/local/bin/python3 /app/reset_timer.py >> /var/log/cron.log 2>&1" | crontab -

# Start cron in background
cron

echo "Starting router watchdog..."
echo "  - Cron job: every 15 minutes"
echo "  - Monitor: listening for power events"

# Run monitor in foreground
exec python3 /app/monitor.py
