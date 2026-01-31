#!/usr/bin/env python3
"""
Shared configuration and MQTT utilities for router watchdog.
"""

import os
import sys
import ssl
import time
import threading
import paho.mqtt.client as mqtt

# Required environment variables
REQUIRED_VARS = ["BROKER", "USERNAME", "PASSWORD", "DEVICE_TOPIC"]


def load_config():
    """Load and validate configuration from environment variables."""
    missing = [var for var in REQUIRED_VARS if not os.environ.get(var)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Set them in .env file or export them before running.", file=sys.stderr)
        sys.exit(1)

    return {
        "broker": os.environ["BROKER"],
        "port": int(os.environ.get("BROKERPORT", "8883")),
        "username": os.environ["USERNAME"],
        "password": os.environ["PASSWORD"],
        "device_topic": os.environ["DEVICE_TOPIC"],
        "timer_seconds": int(os.environ.get("TIMER_SECONDS", "1920")),
        "log_file": os.environ.get("LOG_FILE", "/var/log/router-watchdog.log"),
    }


def create_mqtt_client(client_id: str, config: dict) -> mqtt.Client:
    """Create and configure an MQTT client."""
    client = mqtt.Client(client_id=client_id)
    client.username_pw_set(config["username"], config["password"])
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    return client


def mqtt_publish_and_wait(config: dict, client_id: str, publish_fn, timeout: float = 5.0) -> dict:
    """
    Connect to MQTT, execute publish function, wait for ack, disconnect.

    Args:
        config: Configuration dict
        client_id: MQTT client ID
        publish_fn: Function that takes (client, device_topic) and publishes messages
        timeout: How long to wait for acknowledgment

    Returns:
        dict with 'success', 'acks', and 'error' keys
    """
    result = {"success": False, "acks": [], "error": None}
    got_ack = threading.Event()
    device_topic = config["device_topic"]

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe(f"stat/{device_topic}/#")
            publish_fn(client, device_topic)
        else:
            result["error"] = f"Connection failed with code {rc}"

    def on_message(client, userdata, msg):
        if msg.topic.startswith(f"stat/{device_topic}/"):
            payload = msg.payload.decode("utf-8", errors="ignore")
            result["acks"].append({"topic": msg.topic, "payload": payload})
            result["success"] = True
            got_ack.set()

    client = create_mqtt_client(client_id, config)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(config["broker"], config["port"], keepalive=30)
        client.loop_start()
        got_ack.wait(timeout=timeout)
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        result["error"] = str(e)

    return result
