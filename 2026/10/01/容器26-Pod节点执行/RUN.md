# 26 由 Pod UID 追到进程

状态：`NOT_RUN`。只在独立 kind 实验 VM；在本篇同名素材目录先用 `sha256sum -c CHECKSUMS.sha256` 和 `sha256sum -c C26_CHECKSUMS.sha256` 检查字节，再解压其中的 `probe_app.py` 与 `Dockerfile.single`。按 13 的步骤以固定基础镜像摘要构建、推送到本次实验专用 registry，保存实际平台 manifest digest；不要把本地 Docker image ID（config digest）当成 registry manifest digest。固定 kind/Kubernetes/containerd/CNI 版本和实际镜像/插件版本，源码阅读定点见版本台账；**不得用本机 v1.33.4 阅读定点直接推断未来 VM 的版本或 shim 数量**。本篇 `c26-probe-pod.yaml` 独立可取得，镜像值故意不能直接运行，必须替换为实验者真正构建、kind 节点能按 digest 拉取的 probe-app。

## 创建范围和请求结果

在专用 VM 的工作目录保存 manifest、归档与原始记录，先确认 `OWN_NAMESPACE` 尚不存在；若已有同名命名空间，停止并换名，绝不清理别人创建的对象。`PROBE_IMAGE` 必须是带 64 位十六进制 sha256 摘要的完整引用，例如 `registry.lab.invalid/c26-probe@sha256:<真实摘要>`，且已按 Dockerfile 把程序绑定到 `0.0.0.0:18080`。将以下占位符替换为**实际镜像引用**，不要执行示例域名。

```sh
set -eu
OWN_NAMESPACE=c26-dedicated
OWN_POD=c26-probe
OWN_CONTAINER_NAME=probe
: "${PROBE_IMAGE:?必须先设置已推送且能从节点拉取的探针镜像摘要}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-26-evidence.XXXXXX)
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|" c26-probe-pod.yaml > "$OWN_EVIDENCE/pod.yaml"
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/pod.yaml"
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/"$OWN_POD" --timeout=120s
kubectl -n "$OWN_NAMESPACE" exec "$OWN_POD" -c probe -- python3 -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:18080/identity", timeout=3).read().decode())'
kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD" -o json > "$OWN_EVIDENCE/pod.json"
```

如果等待超时，保存当时 `kubectl describe pod`、`kubectl get events --sort-by=.lastTimestamp` 与容器/镜像拉取状态，**不跳过失败**直接套用下面要求存在 `containerID` 的正常分支命令。应用内 `/identity` 返回的是容器视角 PID 和 namespace inode，不是 VM 宿主 PID。

## 关联 Pod UID、sandbox、容器和进程

正常分支在节点上的 Docker provider 执行下列采样；命名空间内可有其它应用，但不能用名称近似匹配取第一条：

```sh
: "${OWN_NAMESPACE:?请设置自建命名空间}"
: "${OWN_POD:?请设置自建 Pod 名称}"
: "${OWN_CONTAINER_NAME:?请设置该 Pod 中的 probe-app 容器名称}"
kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD" -o json > "$OWN_EVIDENCE/pod.json"
OWN_NODE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"]["nodeName"])' "$OWN_EVIDENCE/pod.json")
OWN_POD_UID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["metadata"]["uid"])' "$OWN_EVIDENCE/pod.json")
OWN_CONTAINER_URI=$(python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(next(c["containerID"] for c in p["status"]["containerStatuses"] if c["name"] == sys.argv[2]))' "$OWN_EVIDENCE/pod.json" "$OWN_CONTAINER_NAME")
case "$OWN_CONTAINER_URI" in containerd://?*) OWN_CONTAINER_ID=${OWN_CONTAINER_URI#containerd://} ;; *) printf '非 containerd 容器 ID: %s\n' "$OWN_CONTAINER_URI"; exit 1 ;; esac
docker inspect "$OWN_NODE" --format '{{.Name}} {{.State.Pid}} {{json .Config.Labels}}'
docker exec "$OWN_NODE" crictl pods --namespace "$OWN_NAMESPACE" --name "$OWN_POD" -o json > "$OWN_EVIDENCE/sandboxes.json"
OWN_SANDBOX_ID=$(python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); ids=[s["id"] for s in p["items"] if s["metadata"]["uid"] == sys.argv[2] and s["state"] == "SANDBOX_READY"]; assert len(ids) == 1, ids; print(ids[0])' "$OWN_EVIDENCE/sandboxes.json" "$OWN_POD_UID")
docker exec "$OWN_NODE" crictl inspectp "$OWN_SANDBOX_ID" > "$OWN_EVIDENCE/sandbox.json"
docker exec "$OWN_NODE" crictl ps -a
docker exec "$OWN_NODE" crictl inspect "$OWN_CONTAINER_ID" > "$OWN_EVIDENCE/container.json"
OWN_NODE_PID=$(python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); assert c["status"]["labels"]["io.kubernetes.pod.uid"] == sys.argv[2]; p=int(c["info"]["pid"]); assert p > 0; print(p)' "$OWN_EVIDENCE/container.json" "$OWN_POD_UID")
docker exec "$OWN_NODE" readlink "/proc/$OWN_NODE_PID/ns/pid" "/proc/$OWN_NODE_PID/ns/mnt" "/proc/$OWN_NODE_PID/ns/net"
docker exec "$OWN_NODE" cat "/proc/$OWN_NODE_PID/cgroup"
```

先确认 `OWN_NODE` 是该专用 kind 集群的节点容器；这里使用 Docker provider，在实际被调度节点内调用 crictl，不能直接连接外侧 VM 的 CRI。`OWN_NODE_PID` 是该节点容器所见的 PID，其 `/proc` 也必须经 `docker exec "$OWN_NODE"` 读取；`docker inspect` 的 `.State.Pid` 是 kind 节点 init 在外侧 Docker daemon 所在 Linux VM 中的 PID，不能替代 probe-app 的外侧 PID。需要跨层映射时另采 `NSpid`/namespace inode，不把节点内 PID 直接拼到外侧 VM 的 `/proc`。

从保存的 Pod UID、sandbox metadata UID/ID、容器 ID 到节点内 PID、ns inode、cgroup、镜像 digest 做一行关联；sandbox 名称筛选只缩小范围，仍需用 UID 对照 `sandboxes.json`。同名重建时重新采样所有值；删除只属于实验的 Pod/namespace 并核对对象清理。当前无 kind/CRI，全部 `NOT_RUN`。

## 失败对照及收尾

在同一专用命名空间新建 **c26-bad**，使用完全相同的 manifest digest，但用不存在的入口命令。`kubectl run` 能创建 API 对象不意味着 sandbox/CNI 必然成功；在节点用 `crictl pods`、`crictl ps -a`、`crictl inspect` 和 Pod 事件分别确认实际失败阶段。若尚无容器 ID，**不要**运行前述解析正常容器 PID 的命令。

```sh
kubectl -n "$OWN_NAMESPACE" run c26-bad --restart=Never --image="$PROBE_IMAGE" --command -- /__c26_missing_executable__
kubectl -n "$OWN_NAMESPACE" describe pod c26-bad > "$OWN_EVIDENCE/bad-describe.txt"
kubectl -n "$OWN_NAMESPACE" get pod c26-bad -o json > "$OWN_EVIDENCE/bad-pod.json"
OWN_BAD_NODE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"].get("nodeName", ""))' "$OWN_EVIDENCE/bad-pod.json")
if test -n "$OWN_BAD_NODE"; then
  docker exec "$OWN_BAD_NODE" crictl pods --namespace "$OWN_NAMESPACE" -o json > "$OWN_EVIDENCE/bad-sandboxes.json"
  docker exec "$OWN_BAD_NODE" crictl ps -a > "$OWN_EVIDENCE/bad-containers.txt"
fi
kubectl -n "$OWN_NAMESPACE" delete pod "$OWN_POD" c26-bad --wait=true --timeout=120s
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=120s
```

若失败发生于 sandbox 或镜像拉取而非入口 `exec`，如实保留其事件和未完成的目标故障，不写预设的 `CreateContainerError`。删除前记录起止 UTC、集群/节点版本、镜像 digest、原始 JSON、HTTP 返回、全部命令退出码；删除后在节点再次按原 UID 检查 CRI 残留。命名空间的归属必须来自本次 `kubectl create` 成功的记录；如中途失败，只针对已创建的本篇对象逐个检查/清理，不删除共享节点的容器或 CNI 配置。专用 VM 从未提供，以上步骤和完整实验保持 `NOT_RUN`。
