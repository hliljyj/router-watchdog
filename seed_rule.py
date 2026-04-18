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

def seed_rule() -> bool:
    """Program Rule1 and Rule2 into the Tasmota device."""
    timer = config["timer_seconds"]
    boot_timer = timer
    fallback_timer = timer * 2

    rule1 = (
        f"ON System#Boot DO RuleTimer1 {boot_timer} ENDON "
        f"ON Rules#Timer=1 DO Backlog Power Off; Delay 300; Power On; RuleTimer1 {fallback_timer} ENDON"
    )
    rule2 = f"ON Ping#google.com#Reachable==1 DO RuleTimer1 {timer} ENDON"

    def publish(client, device_topic):
        # Set Rule1 (dead man's switch)
        client.publish(f"cmnd/{device_topic}/Rule1", rule1, qos=0)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule1", "1", qos=0)
        # Set Rule2 (DNS ping resets timer)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule2", rule2, qos=0)
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/Rule2", "1", qos=0)
        # Start timer
        time.sleep(0.5)
        client.publish(f"cmnd/{device_topic}/RuleTimer1", str(fallback_timer), qos=0)

    result = mqtt_publish_and_wait(
        config=config,
        client_id=f"router-wd-seed-{int(time.time())}",
        publish_fn=publish,
        timeout=10.0,
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
