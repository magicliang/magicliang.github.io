import argparse
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request


def snapshot():
    root = pathlib.Path("/sys/fs/cgroup")
    return {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "monotonic_ns": time.monotonic_ns(),
        "self_cgroup": pathlib.Path("/proc/self/cgroup").read_text(),
        "cgroup_namespace": os.readlink("/proc/self/ns/cgroup"),
        "cpu_stat": (root / "cpu.stat").read_text(),
        "memory_events": (root / "memory.events").read_text(),
        "io_stat": (root / "io.stat").read_text(),
    }


def request(path):
    started = time.monotonic_ns()
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with urllib.request.urlopen("http://127.0.0.1:18080" + path, timeout=1) as response:
            return {"status": response.status, "body": response.read(2048).decode(),
                    "started_utc": started_utc, "started_monotonic_ns": started,
                    "duration_ns": time.monotonic_ns() - started}
    except (OSError, urllib.error.URLError) as error:
        return {"error": repr(error), "started_utc": started_utc,
                "started_monotonic_ns": started, "duration_ns": time.monotonic_ns() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load", action="store_true")
    args = parser.parse_args()
    result = {"load": args.load, "identity": request("/identity"), "before": snapshot()}
    worker = None
    if args.load:
        worker = subprocess.Popen([sys.executable, "/app/bounded_load.py", "--seconds", "2"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    result["requests"] = []
    for _ in range(10):
        result["requests"].append(request("/ready"))
        time.sleep(0.1)
    result["after"] = snapshot()
    if worker is not None:
        output, error = worker.communicate(timeout=5)
        result["worker"] = {"exit": worker.returncode, "stdout": output, "stderr": error}
    print(json.dumps(result, ensure_ascii=False))
    if worker is not None and worker.returncode != 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
