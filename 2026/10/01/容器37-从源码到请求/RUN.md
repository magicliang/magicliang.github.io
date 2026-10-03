# 37 一次请求的完整证据链

仅在本任务独占 Linux VM + 自建 registry + 本任务独占 kind 集群中使用；固定 Docker、kubelet、containerd、CRI/CNI/CSI 及基础镜像版本。先按 12、13 的 RUN 用本次构建镜像完成真实 push，保存本次成功推送的 manifest digest、平台索引及仓库回包，不得沿用历史镜像 tag、未推送的本地 image ID 或占位摘要。此环境缺 docker/kubectl/CSI，命令**未运行**。本篇探针只能接收自有合成文本，不使用共享宿主网络、默认防火墙或其他任务卷。

所有代码块须在**同一个 Bash shell**、仓库 `source/_posts/2026-10-01-容器37-从源码到请求` 目录内运行。每一步在本次工作目录保存 UTC 起止、完整命令、stdout/stderr 与退出码；任一步失败先保留现场，查本轮 Pod UID/容器 ID，再决定是否仅清理自己的对象。`c37_check.py` 是两轮 JSON 一致性的静态断言，不能证明录入的 JSON 真来自同一节点或一次真实请求。

## 准备与基线

准备 `PROBE_IMAGE=repo@sha256:<本轮推送成功的 64 位 digest>`、`STORAGE_CLASS_NAME=<已安装 CSI 的存储类>`、`KUBE_CONTEXT=<本任务独占 kind 集群>`；固定选定平台 manifest、真实节点的 containerd/crictl 版本和客户端路由插件。先校验该 StorageClass 的 provisioner 对应实际 CSI driver。以下只创建新 namespace 和新空 PVC；一旦发现同名对象中止，不覆盖已有卷。

```bash
set -euo pipefail
: "${PROBE_IMAGE:?need successful push manifest digest}" "${STORAGE_CLASS_NAME:?need CSI StorageClass}" "${KUBE_CONTEXT:?need dedicated kind context}"
export PROBE_IMAGE STORAGE_CLASS_NAME
python3 -c 'import os,re; assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}",os.environ["PROBE_IMAGE"])'
sha256sum -c CHECKSUMS.sha256 C37_CHECKSUMS.sha256
OWN_LAB_ROOT="$(git rev-parse --show-toplevel)/examples/containers/.lab-work/37"
mkdir -p "$OWN_LAB_ROOT"
test ! -L "$OWN_LAB_ROOT"
chmod 700 "$OWN_LAB_ROOT"
OWN_WORK=$(mktemp -d "$OWN_LAB_ROOT/round.XXXXXX")
OWN_NAMESPACE="containers37-${OWN_WORK##*.}"
OWN_VALUE="c37-synthetic-${OWN_WORK##*.}"
export OWN_WORK OWN_NAMESPACE OWN_VALUE
k() { kubectl --context "$KUBE_CONTEXT" --request-timeout=30s "$@"; }
kn() { k -n "$OWN_NAMESPACE" "$@"; }
test -z "$(k get namespace "$OWN_NAMESPACE" --ignore-not-found -o name)"
k version -o yaml > "$OWN_WORK/kubernetes-version.yaml"
k get storageclass "$STORAGE_CLASS_NAME" -o json > "$OWN_WORK/storageclass.json"
python3 - <<'PY'
import os
from pathlib import Path
source = Path('c37-k8s.yaml').read_text()
for name in ('OWN_NAMESPACE', 'STORAGE_CLASS_NAME', 'PROBE_IMAGE'):
    source = source.replace('${' + name + '}', os.environ[name])
assert '${' not in source
(Path(os.environ['OWN_WORK']) / 'rendered.yaml').write_text(source)
PY
k create -f "$OWN_WORK/rendered.yaml" > "$OWN_WORK/create.stdout" 2> "$OWN_WORK/create.stderr"
kn rollout status deployment/probe --timeout=120s > "$OWN_WORK/rollout-before.stdout" 2> "$OWN_WORK/rollout-before.stderr"
kn wait pod/client --for=condition=Ready --timeout=120s
```

独立客户端 Pod 用同一个可信镜像提供 Python 标准库 HTTP 客户端，但它**不挂载**服务状态卷。下面按 Service 名称请求，另在服务 Pod 获取自身 `/identity` 与 mountinfo；请求原始 JSON 不得替换为描述文件中的预期值。先记录 PVC/PV/Pod/EndpointSlice、Service 与节点，以便回查错路由、旧后端和错误挂载。

```bash
OWN_POD_BEFORE=$(kn get pod -l app=c37-probe -o jsonpath='{.items[0].metadata.name}')
test -n "$OWN_POD_BEFORE"
kn get pod "$OWN_POD_BEFORE" -o json > "$OWN_WORK/before-pod.json"
kn get pvc state -o json > "$OWN_WORK/before-pvc.json"
OWN_PV=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"]["volumeName"])' "$OWN_WORK/before-pvc.json")
test -n "$OWN_PV"
k get pv "$OWN_PV" -o json > "$OWN_WORK/before-pv.json"
kn get service probe -o json > "$OWN_WORK/before-service.json"
kn get endpointslice -l kubernetes.io/service-name=probe -o json > "$OWN_WORK/before-endpoints.json"
c37_request() {
  kn exec client -- python3 -c 'import json,sys,urllib.request; payload=sys.argv[2].encode() if len(sys.argv)>2 else None; response=urllib.request.urlopen(urllib.request.Request(sys.argv[1],data=payload),timeout=5); print(json.dumps({"status":response.status,"body":json.load(response)}))' "$@"
}
c37_request http://probe:18080/identity > "$OWN_WORK/before-identity.json"
c37_request http://probe:18080/state "$OWN_VALUE" > "$OWN_WORK/before-write.json"
c37_request http://probe:18080/state > "$OWN_WORK/before-state.json"
kn exec "$OWN_POD_BEFORE" -- cat /proc/self/mountinfo > "$OWN_WORK/before-mountinfo.txt"
kn logs "$OWN_POD_BEFORE" > "$OWN_WORK/before-logs.txt"
```

## 到实际调度节点找 CRI/PID

每次读取实际 Pod 的 `.spec.nodeName`，只进入该节点。以下假设该 kind 节点就是自己创建的 Docker 节点容器，必须先核对 `docker inspect "$OWN_NODE"` 的 ID、节点名和 `/etc/crictl.yaml` 的 socket；非 Docker 驱动或 socket 不匹配时暂停并标 `NOT_RUN`，不在操作者宿主的默认 socket 乱查。`crictl` 返回的信息布局随实际插件版本变化：提取 PID 前先人工检查原始 `inspect` 是否把它置于 `info.pid`，不能用猜测的路径在其他节点碰巧找到 PID。节点容器内 `/proc` 是**节点视角**，也不一定是外层 VM 宿主 PID 视角。第二次重建仍须重新读 nodeName。

```bash
c37_node_snapshot() {
  local phase="$1" podfile="$2" node container_id pid
  node=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"]["nodeName"])' "$podfile")
  container_id=$(python3 -c 'import json,sys; s=json.load(open(sys.argv[1]))["status"]["containerStatuses"]; print(next(x["containerID"].split("://",1)[-1] for x in s if x["name"]=="probe"))' "$podfile")
  test -n "$node" && test -n "$container_id"
  docker inspect "$node" > "$OWN_WORK/node-$phase.json"
  docker exec "$node" crictl version > "$OWN_WORK/crictl-version-$phase.txt"
  docker exec "$node" crictl pods -o json > "$OWN_WORK/sandboxes-$phase.json"
  docker exec "$node" crictl inspect "$container_id" > "$OWN_WORK/cri-$phase.json"
  pid=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["info"]["pid"])' "$OWN_WORK/cri-$phase.json")
  test "$pid" -gt 0
  docker exec "$node" cat "/proc/$pid/stat" > "$OWN_WORK/pid-stat-$phase.txt"
  docker exec "$node" cat "/proc/$pid/cgroup" > "$OWN_WORK/pid-cgroup-$phase.txt"
  docker exec "$node" readlink "/proc/$pid/ns/net" > "$OWN_WORK/pid-netns-$phase.txt"
  docker exec "$node" readlink "/proc/$pid/ns/mnt" > "$OWN_WORK/pid-mntns-$phase.txt"
  docker exec "$node" readlink "/proc/$pid/ns/pid" > "$OWN_WORK/pid-pidns-$phase.txt"
  docker exec "$node" cat "/proc/$pid/stat" > "$OWN_WORK/pid-stat-recheck-$phase.txt"
}
c37_node_snapshot before "$OWN_WORK/before-pod.json"
```

对照 `before-pod.json` 的 Pod UID、`sandboxes-before.json` 中标有同 UID 的 sandbox、`cri-before.json` 的业务容器 ID 与节点内 PID；`pid-stat-*.txt` 第 22 字段（启动 tick）前后复核。`/identity` 返回的进程内 PID 不必等于节点 PID，但 netns/mntns/pidns inode 应对应；cgroup 路径记录节点位置而非推算系统版式。确有重复启动时重新取证，不把两个 UID 拼成一条链。

## 保留卷的重建与一致性检查

仅删除本轮服务 Pod，不删 PVC；由本轮 Deployment 创建新 Pod，等待 Ready 和 Service 后端更新，关闭旧客户端连接并重新请求。若存储类的卷不能在新调度节点挂载，把 Pending 和事件记为 `NOT_RUN` 的断点，不删除 PVC 伪造成功。该清单 `Recreate` 单副本并不承诺请求不中断。两轮 state 的 JSON 与 Pod/PVC/PV 原始 JSON 可交给 `c37_check.py` 做**一致性静态断言**，检查失败不得解释为“CRI 一定坏了”。

```bash
kn delete pod "$OWN_POD_BEFORE" --wait=true > "$OWN_WORK/delete-before.stdout" 2> "$OWN_WORK/delete-before.stderr"
kn rollout status deployment/probe --timeout=120s
OWN_POD_AFTER=$(kn get pod -l app=c37-probe -o jsonpath='{.items[0].metadata.name}')
test -n "$OWN_POD_AFTER" && test "$OWN_POD_AFTER" != "$OWN_POD_BEFORE"
kn get pod "$OWN_POD_AFTER" -o json > "$OWN_WORK/after-pod.json"
kn get pvc state -o json > "$OWN_WORK/after-pvc.json"
k get pv "$OWN_PV" -o json > "$OWN_WORK/after-pv.json"
kn get endpointslice -l kubernetes.io/service-name=probe -o json > "$OWN_WORK/after-endpoints.json"
c37_request http://probe:18080/identity > "$OWN_WORK/after-identity.json"
c37_request http://probe:18080/state > "$OWN_WORK/after-state.json"
c37_node_snapshot after "$OWN_WORK/after-pod.json"
python3 c37_check.py --before-pod "$OWN_WORK/before-pod.json" --after-pod "$OWN_WORK/after-pod.json" --before-pvc "$OWN_WORK/before-pvc.json" --after-pvc "$OWN_WORK/after-pvc.json" --before-pv "$OWN_WORK/before-pv.json" --after-pv "$OWN_WORK/after-pv.json" --before-state "$OWN_WORK/before-state.json" --after-state "$OWN_WORK/after-state.json" --expected-value "$OWN_VALUE" > "$OWN_WORK/consistency.txt"
```

逐步负例：在**同一 namespace 的副本 Deployment** 单独把探针监听改为回环，再从本轮 client 请求该 Service；不要直接覆盖正常实例同时改 PVC/镜像。另一负例不挂载 PVC，但保留相同 state-dir，若新 Pod 能本地写入，必须再重建并对照丢失数据。负例对象需有本轮专用名字，先检查冲突，再保存失败 HTTP、Pod UID、mountinfo、事件和清理结果。环境不支持负例时明确写 `NOT_RUN`，不能凭预测填结果。

完成后先停止本轮客户端与服务，保存 Pod/EndpointSlice/PVC/PV、CRI 和请求原始输出；保留 PVC 及其合成数据供复核。仅在核对自建 namespace、卷的 reclaimPolicy、确认数据可丢弃后，才能单独删除本轮 namespace/PVC，并检查底层 PV 与节点是否留有挂载；绝不批量删除镜像、默认 namespace、全局 iptables、宿主 cgroup。无法完成收尾时记录未清理对象及本轮 `OWN_WORK` 路径，不能标“已清理”。此云端 Docker/registry/kind/CSI/CRI 观测均 `NOT_RUN`。
