import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time


def environment():
    root = pathlib.Path("/sys/fs/cgroup")
    paths = ("cpu.max", "cpuset.cpus.effective", "memory.max", "cpu.stat")
    return {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version,
        "platform": os.uname().machine,
        "affinity": sorted(os.sched_getaffinity(0)),
        "self_cgroup": pathlib.Path("/proc/self/cgroup").read_text(),
        "controllers": {name: (root / name).read_text() if (root / name).exists() else None
                        for name in paths},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=pathlib.Path, required=True)
    parser.add_argument("--rounds", type=int, default=1)
    args = parser.parse_args()
    if not args.workload.is_file() or not 1 <= args.rounds <= 20:
        parser.error("workload file and 1..20 rounds are required")
    payload = args.workload.read_bytes()
    report = {"workload_sha256": hashlib.sha256(payload).hexdigest(),
              "before": environment(), "rounds": []}
    for _ in range(args.rounds):
        started = time.monotonic_ns()
        try:
            process = subprocess.run(
                [sys.executable, str(args.workload), "--seconds", "1", "--memory-mib", "8"],
                capture_output=True, text=True, timeout=5, check=False)
            output = process.stdout
            exit_code = process.returncode
            error = process.stderr
        except subprocess.TimeoutExpired as failure:
            output = str(failure.stdout)
            error = str(failure.stderr)
            exit_code = "TIMEOUT"
        match = re.fullmatch(r"iterations=(\d+) seconds=([\d.]+) memory_mib=8\s*", output)
        report["rounds"].append({"start_ns": started, "elapsed_ns": time.monotonic_ns() - started,
                                 "exit": exit_code, "stdout": output, "stderr": error,
                                 "iterations_per_second": int(match.group(1)) / float(match.group(2))
                                 if match and float(match.group(2)) > 0 else None})
    report["after"] = environment()
    print(json.dumps(report, ensure_ascii=False))
    return 0 if all(row["exit"] == 0 and row["iterations_per_second"] is not None for row in report["rounds"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
