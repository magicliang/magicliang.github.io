# 26 由 Pod UID 追到进程

只在独立 kind 实验 VM；先核对 `CHECKSUMS.sha256` 再解压源码包，用 13 的 Dockerfile 构建完整镜像并记录真实 digest。固定 kind/Kubernetes/containerd/CNI 版本及对应源码 tag/commit，不能从滚动文档推断本机 shim 数量。运行自己命名空间下的 probe-app：

```sh
set -eu
: "${OWN_NAMESPACE:?请设置自建命名空间}"
: "${OWN_POD:?请设置自建 Pod 名称}"
: "${OWN_CONTAINER_NAME:?请设置该 Pod 中的 probe-app 容器名称}"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-26-evidence.XXXXXX)
kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD" -o json > "$OWN_EVIDENCE/pod.json"
OWN_NODE=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"]["nodeName"])' "$OWN_EVIDENCE/pod.json")
OWN_POD_UID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["metadata"]["uid"])' "$OWN_EVIDENCE/pod.json")
OWN_CONTAINER_URI=$(python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(next(c["containerID"] for c in p["status"]["containerStatuses"] if c["name"] == sys.argv[2]))' "$OWN_EVIDENCE/pod.json" "$OWN_CONTAINER_NAME")
case "$OWN_CONTAINER_URI" in containerd://?*) OWN_CONTAINER_ID=${OWN_CONTAINER_URI#containerd://} ;; *) printf '非 containerd 容器 ID: %s\n' "$OWN_CONTAINER_URI"; exit 1 ;; esac
docker inspect "$OWN_NODE" --format '{{.Name}} {{.State.Pid}} {{json .Config.Labels}}'
docker exec "$OWN_NODE" crictl pods --namespace "$OWN_NAMESPACE" --name "$OWN_POD" -o json > "$OWN_EVIDENCE/sandboxes.json"
docker exec "$OWN_NODE" crictl ps -a
docker exec "$OWN_NODE" crictl inspect "$OWN_CONTAINER_ID" > "$OWN_EVIDENCE/container.json"
OWN_NODE_PID=$(python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); assert c["status"]["labels"]["io.kubernetes.pod.uid"] == sys.argv[2]; p=int(c["info"]["pid"]); assert p > 0; print(p)' "$OWN_EVIDENCE/container.json" "$OWN_POD_UID")
docker exec "$OWN_NODE" readlink "/proc/$OWN_NODE_PID/ns/pid" "/proc/$OWN_NODE_PID/ns/mnt" "/proc/$OWN_NODE_PID/ns/net"
docker exec "$OWN_NODE" cat "/proc/$OWN_NODE_PID/cgroup"
```

先确认 `OWN_NODE` 是该专用 kind 集群的节点容器；这里使用 Docker provider，在实际被调度节点内调用 crictl，不能直接连接外侧 VM 的 CRI。`OWN_NODE_PID` 是该节点容器所见的 PID，其 `/proc` 也必须经 `docker exec "$OWN_NODE"` 读取；`docker inspect` 的 `.State.Pid` 是 kind 节点 init 在外侧 Docker daemon 所在 Linux VM 中的 PID，不能替代 probe-app 的外侧 PID。需要跨层映射时另采 `NSpid`/namespace inode，不把节点内 PID 直接拼到外侧 VM 的 `/proc`。

从保存的 Pod UID、sandbox metadata UID/ID、容器 ID 到节点内 PID、ns inode、cgroup、镜像 digest 做一行关联；sandbox 名称筛选只缩小范围，仍需用 UID 对照 `sandboxes.json`。同名重建时重新采样所有值；删除只属于实验的 Pod/namespace 并核对对象清理。当前无 kind/CRI，全部 `NOT_RUN`。
