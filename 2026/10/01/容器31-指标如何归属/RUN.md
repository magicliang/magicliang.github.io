# 31：同容器请求与 cgroup v2 时间窗

状态 `NOT_RUN`。需要独占的 Linux cgroup v2 + kind/CRI VM，先记录真实 Kubernetes/容器运行时版本、节点 cgroup driver、有效 CPU/memory/io 控制器、限额来源和镜像 digest。复用 27 的 `Dockerfile.c27`（只组合包内 `probe_app.py` 与 `bounded_load.py`），以固定 base image digest 构建并推送给 VM 节点；镜像必须包含 `/app/bounded_load.py`。不要把只有 `Dockerfile.single` 的镜像用于此清单。不要在共享节点无界施压；包内负载自身限制两秒。脚本读同容器 `/sys/fs/cgroup`，运行前必须通过 `/proc/self/cgroup`、cgroup namespace inode 与节点进程/CRI 身份核对该挂载指向的 cgroup；否则标记 `NOT_RUN`，不把宿主根 cgroup 当容器指标。

```sh
set -eu
sha256sum -c CHECKSUMS.sha256 C31_CHECKSUMS.sha256
OWN_NAMESPACE=c31-dedicated
: "${PROBE_IMAGE:?填入包含两份共用脚本的真实镜像 digest}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-31-evidence.XXXXXX)
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c31-pods.yaml > "$OWN_EVIDENCE/pods.yaml"
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/pods.yaml"
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c31-wide pod/c31-limited --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pods -o json > "$OWN_EVIDENCE/pods-before.json"
date -u +%FT%TZ > "$OWN_EVIDENCE/start-utc.txt"
```

Pod 无法 Ready 时保存事件、镜像拉取失败与 probe-app 启动日志，再做限定对象清理；不要继续写不存在的指标。用 `kubectl exec -i` 把同篇采样脚本送进正在处理 `/ready` 的容器。每个 Pod 顺序运行基线与有界负载，两阶段都留原始 stdout/错误与对象前后快照。实际节点上如需验证 Pod 父层 cgroup，要通过 `crictl inspect` 映射容器 ID 与宿主 PID，再从该 PID 的 `/proc/<pid>/cgroup` 查真实路径，不能把容器内路径文本照抄当宿主路径；任何一次 UID 或容器 ID 改变应立即分开轮次而不是计算差分。

```sh
for pod in c31-wide c31-limited; do
  kubectl -n "$OWN_NAMESPACE" get pod "$pod" -o json > "$OWN_EVIDENCE/$pod-before.json"
  for phase in baseline load; do
    if test "$phase" = load; then
      kubectl -n "$OWN_NAMESPACE" exec -i "$pod" -c probe -- python3 - --load < c31_sample.py > "$OWN_EVIDENCE/$pod-$phase.json" 2> "$OWN_EVIDENCE/$pod-$phase.stderr"
    else
      kubectl -n "$OWN_NAMESPACE" exec -i "$pod" -c probe -- python3 - < c31_sample.py > "$OWN_EVIDENCE/$pod-$phase.json" 2> "$OWN_EVIDENCE/$pod-$phase.stderr"
    fi
    kubectl -n "$OWN_NAMESPACE" get pod "$pod" -o json > "$OWN_EVIDENCE/$pod-$phase-pod.json"
    kubectl -n "$OWN_NAMESPACE" logs "$pod" -c probe --timestamps > "$OWN_EVIDENCE/$pod-$phase-logs.txt"
  done
done
date -u +%FT%TZ > "$OWN_EVIDENCE/end-utc.txt"
```

若任一 `kubectl exec` 失败，在 `set -e` 下立即停止并**仍执行下方清理**，保留 stderr；不是“请求很快”的证据。每个 JSON 包含请求的 UTC/单调耗时、状态或异常、`/identity`、前后 CPU/memory/io 累计值、worker 输出与退出码；比较同一 Pod/同一 cgroup 实例相应 key 的差值，先核对负数或缺失键、容器重启、两个采样时刻是否覆盖负载。十次 `/ready` 太少，不能报告可信 p99；要强结论须在独占 VM 上增加预先定义的重复轮次和结果表。若需要证明 CPU 节流源于此限额，另存所在节点的父 cgroup `cpu.max` 与实际 CPU 竞争条件；仅凭本篇脚本不能排除父级限额。

失败路径：若 probe-app 未就绪，请核对启动地址/端口和探针，而非把十次请求异常解释成 CPU 节流。若 `io.stat` 缺失，脚本会失败并输出实际文件读取异常，应核实 cgroup v2 挂载及控制器，不能写入虚构零值。若 Pod 重建，则保存两代 UID/containerID/cgroup，在新实例独立重跑，不跨实例相减。清理只操作本篇私有 namespace：

```sh
kubectl -n "$OWN_NAMESPACE" get pods -o json > "$OWN_EVIDENCE/pods-before-cleanup.json"
kubectl -n "$OWN_NAMESPACE" delete pod c31-wide c31-limited --ignore-not-found --wait=true --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pods
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=180s
```

本机缺 kind/CRI、cgroup v2 容器场景，探针请求与计数全部 `NOT_RUN`。脚本语法、YAML 解析和网页构建只构成静态检查，不充作节流或尾延迟数据。
