"""Wait for an asynchronously issued Minecraft placement to become observable."""

import time


def wait_for_block_name(block_at, position, expected_name, timeout=1.0, poll_interval=0.05):
    deadline = time.monotonic() + timeout
    observed_name = None
    while True:
        block = block_at(position)
        observed_name = block["name"] if block is not None else None
        if observed_name == expected_name:
            return True, observed_name
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False, observed_name
        time.sleep(min(poll_interval, remaining))
