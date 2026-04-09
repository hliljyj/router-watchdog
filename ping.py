#!/usr/bin/env python3
"""
Router Watchdog - Ping

Sends a DNS ping command to the Tasmota device via MQTT.
If DNS resolves, Rule2 on the device resets the watchdog timer.
After the ping, queries RuleTimer to confirm the reset.
Run this via cron every 15 minutes.
"""

import json
import sys
import time
from datetime import datetime
from config import load_config, create_mqtt_client

config = load_config()


def _format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]


def log(message: str, *, stream=sys.stdout) -> None:
    print(f"{_format_timestamp()} {message}", file=stream)


def ping() -> bool:
    """Send Ping4 google.com, wait for ping result, then query RuleTimer."""
    import threading

    device_topic = config["device_topic"]
    result = {"ping_ok": None, "timer": None, "error": None}
    ping_done = threading.Event()
    timer_done = threading.Event()

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe(f"stat/{device_topic}/#")
            client.subscribe(f"tele/{device_topic}/#")
            client.publish(f"cmnd/{device_topic}/Ping4", "google.com", qos=0)
        else:
            result["error"] = f"Connection failed with code {rc}"

    def on_message(client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="ignore")

        # Ping result comes on tele topic
        if msg.topic == f"tele/{device_topic}/RESULT":
            try:
                data = json.loads(payload)
                if "Ping" in data and isinstance(data["Ping"], dict):
                    ping_info = data["Ping"]
                    for host, info in ping_info.items():
                        if "Reachable" in info:
                            result["ping_ok"] = info["Reachable"]
                            log(f"Ping {host}: {'OK' if info['Reachable'] else 'FAILED'} (IP: {info.get('IP', '?')})")
                            ping_done.set()
            except json.JSONDecodeError:
                pass

        # Timer result comes on stat topic
        if msg.topic == f"stat/{device_topic}/RESULT":
            try:
                data = json.loads(payload)
                if "T1" in data:
                    result["timer"] = data["T1"]
                    timer_done.set()
            except json.JSONDecodeError:
                pass

    client = create_mqtt_client(f"router-wd-ping-{int(time.time())}", config)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(config["broker"], config["port"], keepalive=30)
        client.loop_start()

        # Wait for ping result (up to 10s)
        ping_done.wait(timeout=10)

        # Query timer to confirm
        client.publish(f"cmnd/{device_topic}/RuleTimer", "", qos=0)
        timer_done.wait(timeout=5)

        client.loop_stop()
        client.disconnect()
    except Exception as e:
        result["error"] = str(e)

    if result["error"]:
        log(f"Error: {result['error']}", stream=sys.stderr)
    elif result["timer"] is not None:
        log(f"RuleTimer1: {result['timer']}s")

    return result["ping_ok"] is True


if __name__ == "__main__":
    success = ping()

    if success:
        log("Ping successful")
        sys.exit(0)

    log("Ping failed, retrying in 60s...", stream=sys.stderr)
    time.sleep(60)
    success = ping()

    if success:
        log("Ping successful (retry)")
        sys.exit(0)
    else:
        log("Ping failed", stream=sys.stderr)
        sys.exit(1)
