# Router Watchdog

A dead man's switch for your home router. Automatically power-cycles your router when it becomes unresponsive, restoring internet connectivity without manual intervention.

## The Problem

Some routers (like BT Hubs) occasionally lose their DNS connection, causing your entire home network to go down. The router appears to be running but can't resolve domains — and the only fix is to restart it.

## The Solution

This service implements a **dead man's switch** using a Tasmota smart plug:

1. A Tasmota smart plug controls power to your router
2. The plug runs a countdown timer (RuleTimer)
3. A cron job on an external server resets the timer via MQTT every 15 minutes
4. If the plug can't receive resets (because your home internet is down), the timer expires and power-cycles your router
5. Router reboots → internet restored → cron reconnects → timer resets

The key insight: the **timer runs locally on the smart plug**. It doesn't need internet to count down or trigger a restart.

```
                    INTERNET
    ┌──────────────────────────────────────────────┐
    │                                              │
    │   ┌─────────────┐       ┌─────────────┐     │
    │   │ VPS Server  │       │ MQTT Broker │     │
    │   │             │──────▶│  (HiveMQ)   │     │
    │   │ sends reset │       │             │     │
    │   │ every 15min │       └──────┬──────┘     │
    │   └─────────────┘              │            │
    │                                │            │
    └────────────────────────────────│────────────┘
                                     │
                                     │ only works when
                                     │ router has internet
                                     ▼
    ┌────────────────────────────────────────────────────┐
    │                    HOME NETWORK                    │
    │                                                    │
    │   ┌─────────────┐          ┌─────────────┐        │
    │   │  BT Hub     │          │ Tasmota     │        │
    │   │  (router)   │◀─────────│ Smart Plug  │        │
    │   │             │  power   │             │        │
    │   └─────────────┘          │ local timer │        │
    │                            │ counts down │        │
    │                            └─────────────┘        │
    └────────────────────────────────────────────────────┘

Normal operation:
  1. VPS sends "reset timer" command to MQTT broker every 15 min
  2. Smart plug receives it via router → resets its local timer
  3. Timer never expires, router stays on

When router loses internet:
  1. Smart plug goes offline (can't reach MQTT broker)
  2. VPS keeps sending resets, but plug can't receive them
  3. Local timer on plug keeps counting down (no internet needed)
  4. Timer expires → plug turns OFF power → waits 30s → turns ON
  5. Router reboots → internet restored → plug reconnects → timer resets
```

## Quick Start (Docker)

### 1. Configure

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
nano .env
```

```
BROKER=your-broker.hivemq.cloud
USERNAME=your_mqtt_user
PASSWORD=your_mqtt_password
DEVICE_TOPIC=tasmota_XXXXXX
TIMER_SECONDS=1920
```

### 2. Seed the Rule (Once)

```bash
docker compose run --rm router-watchdog python3 seed_rule.py
```

### 3. Start

```bash
docker compose up -d
```

The container runs:
- **Cron job** every 15 minutes to reset the timer
- **Monitor** to log power events and restarts

### 4. View Logs

```bash
# Restart events
tail -f logs/router-watchdog.log

# Cron output
tail -f logs/cron.log

# Container logs
docker compose logs -f
```

## Files

| File | Purpose |
|------|---------|
| `config.py` | Shared configuration and MQTT utilities |
| `reset_timer.py` | Resets the watchdog timer (run by cron) |
| `seed_rule.py` | Programs the watchdog rule into the device (run once) |
| `monitor.py` | Logs power events and restarts |
| `Dockerfile` | Container image |
| `docker-compose.yml` | Deployment config |
| `.env.example` | Template for credentials (copy to `.env`) |

## Deploy to VPS

### 1. Build Image Locally

```bash
cd router-watchdog
docker build -t router-watchdog:latest .
docker save router-watchdog:latest | gzip > router-watchdog.tar.gz
```

### 2. Copy to Server

```bash
scp router-watchdog.tar.gz user@your-server:/root/
scp .env user@your-server:/root/router-watchdog/
```

### 3. Run on Server

```bash
# SSH into your server
ssh user@your-server

# Load the image
docker load -i /root/router-watchdog/router-watchdog.tar

# Create logs folder
mkdir -p ~/router-watchdog/logs

# Run the container
docker run -d \
  --name router-watchdog \
  --restart unless-stopped \
  --env-file ~/router-watchdog/.env \
  -v ~/router-watchdog/logs:/var/log \
  router-watchdog:latest
```

### 4. Seed the Rule (First Time Only)

```bash
docker run --rm \
  --env-file ~/router-watchdog/.env \
  router-watchdog:latest \
  python3 seed_rule.py
```

### 5. Verify

```bash
# Check container is running
docker ps

# Check logs
tail -f ~/router-watchdog/logs/router-watchdog.log
```

## Manual Setup (Without Docker)

```bash
# Install
pip install -r requirements.txt

# Seed rule (once)
python3 seed_rule.py

# Add cron job
(crontab -l; echo "*/15 * * * * /usr/bin/python3 $(pwd)/reset_timer.py") | crontab -

# Run monitor (optional, for logging restarts)
python3 monitor.py
```

## How the Tasmota Rule Works

```
ON System#Boot DO RuleTimer1 1800 ENDON
ON Rules#Timer=1 DO Backlog Power Off; Delay 300; Power On; RuleTimer1 3600 ENDON
```

- On boot: Start a 30-minute countdown
- When timer expires: Turn off → wait 30 seconds → turn on → restart timer (1 hour fallback)

The cron job keeps resetting `RuleTimer1` before it expires. If it can't (because internet is down), the timer runs out and triggers the power cycle.

## License

MIT
