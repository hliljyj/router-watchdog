#!/usr/bin/env python3
"""
Router Watchdog - Monitor

Listens for power events and logs when the router is restarted.
Runs continuously as a background service.
"""

import json
import time
import logging
from datetime import datetime
from config import load_config, create_mqtt_client

config = load_config()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config["log_file"]),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class PowerMonitor:
    def __init__(self):
        self.last_power_state = None
        self.power_off_time = None
        self.device_offline_time = None
        self.device_topic = config["device_topic"]

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            logger.info(f"Connected to MQTT broker {config['broker']}")
            client.subscribe(f"stat/{self.device_topic}/POWER")
            client.subscribe(f"stat/{self.device_topic}/RESULT")
            client.subscribe(f"tele/{self.device_topic}/STATE")
            client.subscribe(f"tele/{self.device_topic}/LWT")
        else:
            logger.error(f"Connection failed with code {rc}")

    def on_disconnect(self, client, userdata, rc):
        logger.warning(f"Disconnected from broker (rc={rc}), will reconnect...")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="ignore")
        power_state = self._parse_power_state(msg.topic, payload)

        if power_state:
            self._handle_power_change(power_state)
            return

        lwt_state = self._parse_lwt_state(msg.topic, payload)
        if lwt_state:
            self._handle_lwt_change(lwt_state)

    def _parse_power_state(self, topic: str, payload: str) -> str | None:
        """Extract power state from various MQTT message formats."""
        if topic == f"stat/{self.device_topic}/POWER":
            return payload.upper()

        if topic in (f"stat/{self.device_topic}/RESULT", f"tele/{self.device_topic}/STATE"):
            try:
                data = json.loads(payload)
                if "POWER" in data:
                    return data["POWER"].upper()
            except json.JSONDecodeError:
                pass

        return None

    def _parse_lwt_state(self, topic: str, payload: str) -> str | None:
        """Extract LWT state from Tasmota LWT topic."""
        if topic == f"tele/{self.device_topic}/LWT":
            return payload.upper()
        return None

    def _handle_lwt_change(self, lwt_state: str):
        """Log LWT transitions (Online/Offline) with downtime calculation."""
        now = datetime.now()
        
        if lwt_state == "OFFLINE":
            self.device_offline_time = now
            logger.warning("DEVICE OFFLINE - MQTT LWT indicates disconnect")
        elif lwt_state == "ONLINE":
            if self.device_offline_time:
                downtime = (now - self.device_offline_time).total_seconds()
                logger.info(f"DEVICE ONLINE - was offline for {downtime:.1f}s")
                self.device_offline_time = None
            else:
                logger.info("DEVICE ONLINE - MQTT LWT indicates reconnect")

    def _handle_power_change(self, new_state: str):
        """Log power state transitions."""
        now = datetime.now()

        if new_state == "OFF" and self.last_power_state != "OFF":
            self.power_off_time = now
            logger.warning("POWER OFF - router power cut")

        elif new_state == "ON" and self.last_power_state == "OFF":
            if self.power_off_time:
                downtime = (now - self.power_off_time).total_seconds()
                logger.warning(f"ROUTER RESTARTED - was off for {downtime:.1f}s")
            else:
                logger.warning("POWER ON - router restarted")
            self.power_off_time = None

        self.last_power_state = new_state

    def run(self):
        """Run the monitor loop with auto-reconnect."""
        client = create_mqtt_client(f"router-wd-monitor-{int(time.time())}", config)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message

        logger.info(f"Starting monitor for {self.device_topic}")

        while True:
            try:
                client.connect(config["broker"], config["port"], keepalive=60)
                client.loop_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Connection error: {e}, retrying in 30s...")
                time.sleep(30)


if __name__ == "__main__":
    monitor = PowerMonitor()
    monitor.run()
