#!/usr/bin/env python3
import argparse
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import re
import signal
import sys
import time
import uuid


def counters(text):
    result = {}
    for line in text.splitlines():
        key, value = line.split()
        if key in result or int(value) < 0:
            raise ValueError("invalid counter: " + line)
        result[key] = int(value)
    if "usage_usec" not in result:
        raise ValueError("cpu.stat lacks usage_usec")
    return result


def snapshot(group):
    raw = (group / "cpu.stat").read_text()
    return {"raw": raw, "counters": counters(raw)}


def delta(before, after):
    values = {key: after[key] - value for key, value in before.items()}
    if any(value < 0 for value in values.values()):
        raise ValueError("cpu.stat counter decreased")
    return values


def cgroup_mount(parent, mountinfo):
    matches = []
    for line in mountinfo.splitlines():
        left, right = line.split(" - ", 1)
        fields = left.split()
        if right.split()[0] == "cgroup2":
            mount = Path(re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), fields[4]))
            if parent == mount or mount in parent.parents:
                matches.append(mount)
    if not matches:
        raise ValueError("parent is not on a visible cgroup2 mount")
    return max(matches, key=lambda p: len(p.parts))


def preflight(parent, cpu, delegated):
    if not delegated:
        raise ValueError("explicit --delegated acknowledgement required")
    if sys.platform != "linux":
        raise ValueError("real experiment requires Linux cgroup v2")
    mount = cgroup_mount(parent, Path("/proc/self/mountinfo").read_text())
    if parent == mount:
        raise ValueError("use a delegated non-root cgroup, not the mount root")
    if "cpu" not in (parent / "cgroup.subtree_control").read_text().split():
        raise ValueError("parent must already enable cpu; runner will not enable it")
    if (parent / "cgroup.type").read_text().strip() != "domain":
        raise ValueError("parent must be a domain cgroup")
    if not os.access(parent, os.W_OK | os.X_OK):
        raise ValueError("delegated parent is not writable")
    if cpu not in os.sched_getaffinity(0):
        raise ValueError("requested CPU is outside runner affinity")
    if os.sched_getscheduler(0) != os.SCHED_OTHER:
        raise ValueError("use the ordinary SCHED_OTHER scheduler")
    ancestors = []
    current = parent
    while True:
        entry = {"path": str(current)}
        for name in ("cpu.max", "cpu.weight", "cpu.idle", "cpuset.cpus.effective"):
            path = current / name
            if path.exists():
                entry[name] = path.read_text().strip()
        if current != mount and "cpu.max" not in entry:
            raise ValueError("cannot inspect cpu.max at " + str(current))
        if "cpu.max" in entry and entry["cpu.max"].split()[0] != "max":
            raise ValueError("visible ancestor has CPU quota: " + str(current))
        if entry.get("cpu.idle", "0") != "0":
            raise ValueError("visible ancestor uses cpu.idle: " + str(current))
        ancestors.append(entry)
        if current == mount:
            break
        current = current.parent
    return {"kernel": platform.release(), "mount": str(mount), "ancestors": ancestors,
            "runner_affinity": sorted(os.sched_getaffinity(0)), "nice": os.getpriority(os.PRIO_PROCESS, 0),
            "cpuinfo": Path("/proc/cpuinfo").read_text(),
            "self_cgroup": Path("/proc/self/cgroup").read_text(),
            "hidden_ancestors": "unobservable outside current mount/cgroup namespace"}


def design(repeats):
    for repeat in range(1, repeats + 1):
        cases = [("compete", {"a": 100, "b": 200}), ("solo", {"a": 100}),
                 ("solo_high", {"a": 200}),
                 ("swap", {"a": 200, "b": 100})]
        if repeat % 2 == 0:
            cases.reverse()
        for name, weights in cases:
            order = list(weights)
            if repeat % 2 == 0:
                order.reverse()
            yield {"repeat": repeat, "condition": name, "weights": weights, "launch_order": order}


def worker(group, cpu, seconds, channel):
    try:
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        (group / "cgroup.procs").write_text(str(os.getpid()))
        if str(os.getpid()) not in (group / "cgroup.procs").read_text().split():
            raise RuntimeError("migration readback failed")
        os.sched_setaffinity(0, {cpu})
        if os.sched_getaffinity(0) != {cpu}:
            raise RuntimeError("affinity readback failed")
        channel.send({"ready": True, "pid": os.getpid(), "affinity": [cpu], "migrated": True})
        if not channel.poll(5):
            raise TimeoutError("no common start received")
        start = channel.recv()
        time.sleep(max(0, start - time.monotonic()))
        actual_start = time.monotonic()
        deadline = start + seconds
        work = 0
        value = 1
        cpu_start = time.process_time()
        while time.monotonic() < deadline:
            value = (value * 1664525 + 1013904223) & 0xffffffff
            work += 1
        actual_end = time.monotonic()
        channel.send({"work_units": work, "checksum": value, "scheduled_start": start,
                      "actual_start": actual_start, "actual_end": actual_end,
                      "elapsed_seconds": actual_end - actual_start,
                      "start_lateness_seconds": actual_start - start,
                      "process_cpu_seconds": time.process_time() - cpu_start})
    except BaseException as error:
        channel.send({"error": repr(error)})
        raise
    finally:
        channel.close()


def receive(channel, deadline):
    if not channel.poll(max(0, deadline - time.monotonic())):
        raise TimeoutError("worker did not answer before deadline")
    message = channel.recv()
    if "error" in message:
        raise RuntimeError(message["error"])
    return message


def run_round(groups, case, cpu, seconds, record):
    round_start = time.monotonic()
    context = mp.get_context("spawn")
    processes, channels = {}, {}
    record.update(case, workers={}, status="FAILED")
    try:
        for label in case["launch_order"]:
            group = groups[label]
            (group / "cpu.weight").write_text(str(case["weights"][label]))
            actual_weight = int((group / "cpu.weight").read_text())
            if actual_weight != case["weights"][label]:
                raise RuntimeError("weight readback mismatch")
            parent_end, child_end = context.Pipe()
            channels[label] = parent_end
            process = context.Process(target=worker, args=(group, cpu, seconds, child_end))
            processes[label] = process
            record["workers"][label] = {"weight": actual_weight, "group": str(group)}
            process.start()
            child_end.close()
        ready_deadline = time.monotonic() + 5
        for label, channel in channels.items():
            record["workers"][label]["ready"] = receive(channel, ready_deadline)
        for label in channels:
            record["workers"][label]["before"] = snapshot(groups[label])
        start = time.monotonic() + 0.2
        record["common_start_monotonic"] = start
        for channel in channels.values():
            channel.send(start)
        for label, channel in channels.items():
            record["workers"][label]["load"] = receive(channel, start + seconds + 1)
        for process in processes.values():
            process.join(max(0, start + seconds + 1 - time.monotonic()))
            if process.exitcode != 0:
                raise RuntimeError("worker failed or did not exit")
        record["status"] = "COMPLETED"
    except BaseException as error:
        record["error"] = repr(error)
        raise
    finally:
        for label, process in processes.items():
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                    process.join(0.5)
                if process.is_alive():
                    process.kill()
                    process.join(0.5)
                record["workers"][label]["exitcode"] = process.exitcode
            try:
                item = record["workers"][label]
                item["after"] = snapshot(groups[label])
                if "before" in item:
                    item["delta"] = delta(item["before"]["counters"], item["after"]["counters"])
            except Exception as error:
                record["status"] = "FAILED"
                record["collection_error"] = repr(error)
        for channel in channels.values():
            channel.close()
        record["total_elapsed_seconds"] = time.monotonic() - round_start
    if record["status"] != "COMPLETED":
        raise RuntimeError("round collection failed")


def cleanup(owned):
    result = []
    for group in reversed(owned):
        try:
            if (group / "cgroup.procs").read_text().strip():
                raise RuntimeError("group still has processes; refusing removal")
            group.rmdir()
            result.append({"path": str(group), "removed": True})
        except Exception as error:
            result.append({"path": str(group), "removed": False, "error": repr(error)})
    return result


def main():
    parser = argparse.ArgumentParser(description="Bounded cgroup v2 CPU-weight experiment")
    parser.add_argument("--parent", type=Path, required=True, help="existing explicitly delegated writable parent")
    parser.add_argument("--delegated", action="store_true", help="acknowledge parent is delegated to you")
    parser.add_argument("--cpu", type=int, required=True)
    parser.add_argument("--seconds", type=float, default=2)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true", help="design only: no preflight, load or cgroup writes")
    parser.add_argument("--output", type=Path, required=True, help="new JSON file; refuses overwrite")
    args = parser.parse_args()
    if not 0 < args.seconds <= 2 or args.repeats < 10 or args.cpu < 0:
        parser.error("require 0 < seconds <= 2, repeats >= 10 and cpu >= 0")
    if not args.parent.is_absolute():
        parser.error("parent must be an absolute path")
    report = {"status": "NOT_RUN", "rounds": [], "design": list(design(args.repeats)),
              "seconds": args.seconds, "cpu": args.cpu, "parent": str(args.parent),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "official_reference": "https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu"}
    owned = []
    with args.output.open("x") as output:
        try:
            if args.dry_run:
                report["status"] = "DESIGN_ONLY_NOT_RUN"
            else:
                parent = args.parent.resolve(strict=True)
                report["environment"] = preflight(parent, args.cpu, args.delegated)
                root = parent / ("weight-study-" + uuid.uuid4().hex)
                root.mkdir()
                owned.append(root)
                (root / "cgroup.subtree_control").write_text("+cpu")
                groups = {}
                for label in ("a", "b"):
                    group = root / label
                    group.mkdir()
                    owned.append(group)
                    groups[label] = group
                for case in report["design"]:
                    record = {}
                    report["rounds"].append(record)
                    run_round(groups, case, args.cpu, args.seconds, record)
                report["status"] = "COMPLETED_OBSERVATIONS_ONLY"
        except BaseException as error:
            report["status"] = "FAILED"
            report["error"] = repr(error)
        finally:
            report["cleanup"] = cleanup(owned)
            if any(not item["removed"] for item in report["cleanup"]):
                report["status"] = "FAILED"
            report["completed_rounds"] = sum(r["status"] == "COMPLETED" for r in report["rounds"])
            report["failed_rounds"] = len(report["rounds"]) - report["completed_rounds"]
            report["failure_rate_attempted"] = (report["failed_rounds"] / len(report["rounds"])) if report["rounds"] else None
            json.dump(report, output, ensure_ascii=False, indent=2)
            output.write("\n")
    return 1 if report["status"] == "FAILED" else 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit("SIGTERM"))
    sys.exit(main())
