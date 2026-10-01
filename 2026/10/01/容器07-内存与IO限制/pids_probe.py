import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--children", type=int, default=2)
    parser.add_argument("--hold-seconds", type=float, default=0.5)
    args = parser.parse_args()
    if not 0 <= args.children <= 4 or not 0 <= args.hold_seconds <= 2:
        parser.error("children: 0..4; hold-seconds: 0..2")

    children = []
    try:
        for child_number in range(args.children):
            try:
                child = subprocess.Popen(
                    [sys.executable, "-c", "import sys,time; time.sleep(float(sys.argv[1]))", str(args.hold_seconds)]
                )
            except OSError as error:
                print(f"spawn_error={error.errno} created={len(children)}", flush=True)
                return 1
            children.append(child)
            print(f"child_number={child_number} child_pid={child.pid}", flush=True)
        return 0
    finally:
        for child in children:
            child.wait(timeout=4)
        print(f"reaped={len(children)}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
