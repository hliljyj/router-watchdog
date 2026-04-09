#!/usr/bin/env python3
"""
Router Watchdog - Seed Rule

Programs the watchdog rule into the Tasmota device.
Run this once during initial setup.
"""

import sys
import time
from config import load_config, mqtt_publish_and_wait

config = load_config()

RULE1_TEXT = (
    "ON System#Boot DO RuleTimer1 1800 ENDON "
    "ON Rules#Timer=1 DO Backlog Power Off; Delay 300; Power On; RuleTimer1 3600 ENDON"
)

RULE2_TEXT = (
    "ON System#Boot DO RuleTimer2 1800 ENDON "
    "ON Rules#Timer=2 DO Backlog Power Off; Delay 300; Power On; RuleTimer2 3600 ENDON"
)

RULE3_TEXT = (
    "ON Time#Minute|15 DO Ping4 www.google.com ENDON "
    "ON Ping#www.google.com#Reachable==true DO RuleTimer2 1920 ENDON"
)


def seed_rule() -> bool:
    """Program Rule1, Rule2, and Rule3 into the Tasmota device."""

    def publish(client, device_topic):
        # Set Rule1 (dead man's switch)
        client.publish(f"cmnd/{device_topic}/Rule1", RULE1_TEXT, qos=0)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule1", "1", qos=0)
        # Set Rule2 (VPS dead man's switch - only VPS resets RuleTimer2)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule2", RULE2_TEXT, qos=0)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule2", "1", qos=0)
        # Set Rule3 (DNS health check)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule3", RULE3_TEXT, qos=0)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule3", "1", qos=0)
        # Start both timers immediately
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/RuleTimer1", "3600", qos=0)
        client.publish(f"cmnd/{device_topic}/RuleTimer2", "3600", qos=0)

    result = mqtt_publish_and_wait(
        config=config,
        client_id=f"router-wd-seed-{int(time.time())}",
        publish_fn=publish,
    )

    if result["error"]:
        print(f"Error: {result['error']}", file=sys.stderr)

    for ack in result["acks"]:
        print(f"  {ack['topic']}: {ack['payload']}")

    return result["success"]


if __name__ == "__main__":
    print(f"Seeding watchdog rule to {config['device_topic']}...")
    print(f"Broker: {config['broker']}")
    print()

    success = seed_rule()

    if success:
        print("\nRule seeded successfully")
        sys.exit(0)
    else:
        print("\nFailed to seed rule", file=sys.stderr)
        sys.exit(1)
