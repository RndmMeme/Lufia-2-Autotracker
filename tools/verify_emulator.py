"""Read-only live verification harness for the v1.4.6 emulator helper."""

import argparse
import json
import logging
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.helper_interface import HelperInterface  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Probe only this emulator process ID")
    parser.add_argument("--timeout", type=float, default=90, help="Maximum seconds to wait")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    messages = []
    helper_args = ["--pid", str(args.pid)] if args.pid else []
    helper = HelperInterface(messages.append, helper_args)
    helper.start()

    state_payload = None
    deadline = time.time() + args.timeout
    try:
        while time.time() < deadline:
            state_payload = next((item for item in messages if "inventory" in item), None)
            statuses = [item.get("tracker_status", {}).get("state") for item in messages]
            if state_payload is not None or "waiting" in statuses or "error" in statuses:
                break
            time.sleep(0.2)
    finally:
        helper.stop()

    statuses = [item["tracker_status"] for item in messages if "tracker_status" in item]
    print("\nTracker statuses:")
    print(json.dumps(statuses, indent=2))

    if state_payload is None:
        print("\nNo validated game-state payload was received.")
        return 1

    summary = {
        "inventory_count": len(state_payload.get("inventory") or []),
        "characters": state_payload.get("characters") or [],
        "capsules": state_payload.get("capsules") or [],
        "cleared_location_count": len(state_payload.get("cleared_locations") or []),
        "player_x": state_payload.get("player_x"),
        "player_y": state_payload.get("player_y"),
        "transport_mode": state_payload.get("transport_mode"),
        "capsule_sprite_count": len(state_payload.get("capsule_sprite_values") or []),
    }
    print("\nState summary:")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
