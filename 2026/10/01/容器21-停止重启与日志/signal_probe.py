import argparse
import json
import os
import signal
import time
from datetime import datetime, timezone


def emit(event, mode):
    print(
        json.dumps(
            {
                "event": event,
                "mode": mode,
                "pid": os.getpid(),
                "utc": datetime.now(timezone.utc).isoformat(),
                "monotonic": time.monotonic(),
            }
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("graceful", "delayed"), required=True)
    args = parser.parse_args()
    stopping = False

    def on_term(signum, frame):
        nonlocal stopping
        emit("term_received", args.mode)
        if args.mode == "delayed":
            time.sleep(3)
        stopping = True

    signal.signal(signal.SIGTERM, on_term)
    emit("started", args.mode)
    deadline = time.monotonic() + 8
    while not stopping and time.monotonic() < deadline:
        time.sleep(0.1)
    emit("stopped" if stopping else "deadline_reached", args.mode)


if __name__ == "__main__":
    main()
