import argparse
import json
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser()
    for name in ("before_pod", "after_pod", "before_pvc", "after_pvc", "before_pv", "after_pv", "before_state", "after_state"):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--expected-value", required=True)
    arguments = parser.parse_args()
    before_pod = load_json(arguments.before_pod)
    after_pod = load_json(arguments.after_pod)
    before_pvc = load_json(arguments.before_pvc)
    after_pvc = load_json(arguments.after_pvc)
    before_pv = load_json(arguments.before_pv)
    after_pv = load_json(arguments.after_pv)
    assert before_pod["metadata"]["uid"] != after_pod["metadata"]["uid"], "Pod UID unchanged"
    assert before_pod["metadata"]["name"] != after_pod["metadata"]["name"], "Pod name unchanged"
    assert before_pvc["metadata"]["uid"] == after_pvc["metadata"]["uid"], "PVC UID changed"
    assert before_pvc["spec"]["volumeName"] == after_pvc["spec"]["volumeName"], "PV reference changed"
    assert before_pv["metadata"]["uid"] == after_pv["metadata"]["uid"], "PV UID changed"
    for field in ("driver", "volumeHandle"):
        assert before_pv["spec"]["csi"][field] == after_pv["spec"]["csi"][field], f"CSI {field} changed"
    image_before = before_pod["spec"]["containers"][0]["image"]
    image_after = after_pod["spec"]["containers"][0]["image"]
    assert image_before == image_after and "@sha256:" in image_before, "declared image digest changed or missing"
    before_status = before_pod["status"]["containerStatuses"][0]
    after_status = after_pod["status"]["containerStatuses"][0]
    assert before_status["containerID"] != after_status["containerID"], "container ID unchanged"
    assert before_status["imageID"] and after_status["imageID"], "missing observed image ID"
    for state_path in (arguments.before_state, arguments.after_state):
        response = load_json(state_path)
        assert response["status"] == 200 and response["body"]["value"] == arguments.expected_value, f"state mismatch: {state_path}"
    print("STATIC_CONSISTENCY_ONLY: different Pod/container, same declared digest and PVC/PV/CSI handle, two HTTP state results; verify CRI/PID and request provenance separately")


if __name__ == "__main__":
    main()
