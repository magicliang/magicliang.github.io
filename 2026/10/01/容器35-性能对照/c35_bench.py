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


def cgroup_location(self_cgroup, mountinfo):
    memberships = [line.split(":", 2)[2] for line in self_cgroup.splitlines()
                   if line.startswith("0::")]
    if len(memberships) != 1:
        raise ValueError("exactly one cgroup v2 membership is required")
    group = pathlib.PurePosixPath(memberships[0])
    if not group.is_absolute() or ".." in group.parts:
        raise ValueError("cgroup membership is outside the visible namespace")
    candidates = []
    for line in mountinfo.splitlines():
        fields, separator, filesystem = line.partition(" - ")
        if not separator or filesystem.split()[0] != "cgroup2":
            continue
        fields = fields.split()
        mount_root, mount_point = [
            pathlib.PurePosixPath(re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), value))
            for value in fields[3:5]]
        if not mount_root.is_absolute() or not mount_point.is_absolute() or ".." in mount_root.parts:
            continue
        try:
            relative = group.relative_to(mount_root)
        except ValueError:
            continue
        directory = pathlib.Path(mount_point / relative)
        if directory.is_dir():
            candidates.append((len(mount_root.parts), {
                "membership": str(group), "mount_root": str(mount_root),
                "mount_point": str(mount_point), "directory": str(directory),
                "mountinfo_line": line,
            }))
    if not candidates:
        raise ValueError("cannot map cgroup v2 membership to a visible mount; check namespace mounts")
    return max(candidates, key=lambda item: item[0])[1]


def environment():
    self_cgroup = pathlib.Path("/proc/self/cgroup").read_text()
    location = cgroup_location(self_cgroup, pathlib.Path("/proc/self/mountinfo").read_text())
    root = pathlib.Path(location["directory"])
    paths = ("cpu.max", "cpuset.cpus.effective", "memory.max", "cpu.stat")
    return {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version,
        "platform": os.uname().machine,
        "affinity": sorted(os.sched_getaffinity(0)),
        "self_cgroup": self_cgroup,
        "cgroup_source": location,
        "controller_scope": "current cgroup only; ancestor limits (including hidden namespace ancestors) not evaluated",
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
