#!/usr/bin/env python3
"""
Router Watchdog - Reset Timer

Resets the Tasmota RuleTimer to keep the router alive.
Run this via cron every 15 minutes.
"""

import sys
import time
from config import load_config, mqtt_publish_and_wait

config = load_config()


def reset_timer(seconds: int) -> bool:
    """Reset RuleTimer1 to the specified seconds."""

    def publish(client, device_topic):
        client.publish(f"cmnd/{device_topic}/RuleTimer1", str(seconds), qos=0)

    result = mqtt_publish_and_wait(
        config=config,
        client_id=f"router-wd-{int(time.time())}",
        publish_fn=publish,
    )

    if result["error"]:
        print(f"Error: {result['error']}", file=sys.stderr)

    return result["success"]


if __name__ == "__main__":
    timer = config["timer_seconds"]
    success = reset_timer(timer)

    if success:
        print(f"Timer reset to {timer}s")
        sys.exit(0)
    else:
        print("Failed to reset timer", file=sys.stderr)
        sys.exit(1)
