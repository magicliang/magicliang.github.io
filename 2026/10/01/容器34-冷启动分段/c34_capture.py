import argparse
import datetime
import json
import pathlib
import subprocess
import time


def snapshot():
    return {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "monotonic_ns": time.monotonic_ns(),
    }


def command(*arguments):
    before = snapshot()
    try:
        process = subprocess.run(arguments, capture_output=True, text=True, timeout=200, check=False)
        result = {"exit": process.returncode, "stdout": process.stdout, "stderr": process.stderr}
    except subprocess.TimeoutExpired as error:
        result = {"exit": "TIMEOUT", "stdout": str(error.stdout), "stderr": str(error.stderr)}
    return {"before": before, "after": snapshot(), "result": result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--pod", required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.namespace != "c34-dedicated" or not args.pod.startswith("c34-"):
        parser.error("use only the dedicated namespace and a c34- pod")
    result = {"namespace": args.namespace, "pod": args.pod, "manifest": str(args.manifest)}
    base = ("kubectl", "-n", args.namespace)
    result["apply"] = command(*base, "apply", "-f", str(args.manifest))
    if result["apply"]["result"]["exit"] == 0:
        result["ready"] = command(*base, "wait", "--for=condition=Ready", f"pod/{args.pod}", "--timeout=180s")
        result["pod"] = command(*base, "get", "pod", args.pod, "-o", "json")
        if result["ready"]["result"]["exit"] == 0:
            script = "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:18080/ready',timeout=3); print(r.status,r.read().decode())"
            result["http"] = command(*base, "exec", args.pod, "-c", "probe", "--", "python3", "-c", script)
        result["events"] = command(*base, "get", "events", "-o", "json")
        result["logs"] = command(*base, "logs", args.pod, "-c", "probe", "--timestamps")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0 if result.get("ready", {}).get("result", {}).get("exit") == 0 and result.get("http", {}).get("result", {}).get("exit") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
