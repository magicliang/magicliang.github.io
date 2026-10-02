# 34：把 Pod 可见等待与节点内部阶段分开记录

状态：`NOT_RUN`。只在独占 kind/CRI/containerd VM 上操作，以同一可访问 manifest digest 与 probe-app 固定 `--ready-delay=10`。先记录操作系统/架构、节点 UID、Kubernetes/CRI/containerd/snapshotter 版本、镜像 index/平台 manifest digest、镜像仓库位置、节点时钟同步状况与 content/snapshot 原始基线；不得在共享 VM 清空 imagefs、containerd store 或别人的镜像。冷组每轮须由实验环境提供**独立的全新或经管理者核验已清空缓存的专用节点**；否则标 `NOT_RUN`，不把 Pod 重建叫冷启动。热组只在同一固定节点同一摘要上重复，先预热一轮，后取五轮原始样本，并显式报告失败与资源竞争。

`c34_capture.py` 的 t0/t1/t2/t3 都在运行 CLI 的**同一台机器**用单调时钟标注，分别对应 API 创建、Ready 状态观察和 exec 中 HTTP 成功；这些客户端区间**不**等同 layer 下载、snapshot prepare 或 OCI create。`c34-timing.json` 的六个节点内部时段都为 `null`；取得实际节点/CRI/shim 事件并核对时钟之前，不能填数字。源包由 13 的 Dockerfile.single 加工，镜像实际 digest 必须在专用 VM 自己构建/推送得到。

```sh
set -eu
sha256sum -c CHECKSUMS.sha256 C34_CHECKSUMS.sha256
OWN_NAMESPACE=c34-dedicated
: "${PROBE_IMAGE:?填入可访问且固定的 manifest digest}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-34-evidence.XXXXXX)
date -u +%FT%TZ > "$OWN_EVIDENCE/start-utc.txt"
kubectl get nodes -o json > "$OWN_EVIDENCE/nodes-before.json"
```

先创建一次 `c34-prewarm` 并删除，然后对同一节点做五轮串行热组。操作员需要核对每轮 `pod.json` 的 `spec.nodeName` 与第一次相同；若调度漂移，应停止把后续轮次计入这一组，保留原始数据。任一次非零也保留 stderr、事件与 Pod UID，不默默从统计中删去失败样本。脚本本身**不**执行 `kubectl delete`，以便在失败后先取 CRI/node 日志；下列删除操作严格限定本轮具名 Pod。

```sh
for round in prewarm 1 2 3 4 5; do
  OWN_POD="c34-$round"
  sed -e "s|REPLACE_WITH_POD_NAME|$OWN_POD|g" -e "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c34-pod.yaml > "$OWN_EVIDENCE/$OWN_POD.yaml"
  if python3 c34_capture.py --namespace "$OWN_NAMESPACE" --pod "$OWN_POD" --manifest "$OWN_EVIDENCE/$OWN_POD.yaml" --output "$OWN_EVIDENCE/$OWN_POD.json"; then
    printf '%s result=complete\n' "$OWN_POD" >> "$OWN_EVIDENCE/rounds.txt"
  else
    printf '%s result=failed\n' "$OWN_POD" >> "$OWN_EVIDENCE/rounds.txt"
  fi
  kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD" -o yaml > "$OWN_EVIDENCE/$OWN_POD-final.yaml" 2> "$OWN_EVIDENCE/$OWN_POD-get.stderr" || true
  kubectl -n "$OWN_NAMESPACE" delete pod "$OWN_POD" --ignore-not-found --wait=true --timeout=180s
  if test "$round" = prewarm && ! grep -q 'c34-prewarm result=complete' "$OWN_EVIDENCE/rounds.txt"; then
    printf 'prewarm failed; stop before measuring warm cache\n' >&2
    exit 1
  fi
done
date -u +%FT%TZ > "$OWN_EVIDENCE/end-utc.txt"
```

若应用的状态或挂载失败，立即记录并排查，不继续假装“预热完成”；启动过程中未运行 `/ready` 的 Pod 不能作为有效样本。脚本用 `kubectl wait Ready` 测的是观测区间，即使日志里显示 Pulling/Pulled，也不能把它们的 API UTC 直接与本机单调时钟相减。要完成计划中真正的分段，需在实际节点上为同一 Pod UID、containerID、所选 manifest digest 采集 kubelet/CRI/containerd/shim/runc 的原始事件，明确哪一事件在下载、解包、snapshot prepare、OCI create/start 之前/之后，注明每一日志时间源与采样误差；缺失时保留 `null`。

冷组若专用实验室可以交付五台独立新 VM/五次受控干净还原，则在**各自** VM 上核对 `crictl images`、content/snapshot 实体与所属节点的镜像基线，逐台运行同一张 Pod 清单和 `c34_capture.py`，产出的证据目录按 VM ID 分开保存。命令不能自动擦除缓存代替真实干净节点；若环境不足，报告冷组 `NOT_RUN`，热组也只是“同一节点条件下的可见等待”而非完整镜像分段。此处是具体补跑入口，不包含任何猜测时间输出。

```sh
kubectl -n "$OWN_NAMESPACE" delete pod c34-prewarm c34-1 c34-2 c34-3 c34-4 c34-5 --ignore-not-found --wait=true --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pods
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=180s
```

仅清理本篇创建的 Pod/namespace，不动 registry、共享快照或任何 imagefs 内容。云端没有 OCI 运行时或独占 VM，所有请求、重复轮次与节点分段仍 `NOT_RUN`；静态校验、页面构建不能填入分布表。
