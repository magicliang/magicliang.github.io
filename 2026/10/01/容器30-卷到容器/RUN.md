# 30：独占 CSI 卷的绑定、挂载、重建与拒绝路径

状态：`NOT_RUN`。仅在可丢弃卷的专用 kind/CSI 环境操作；记录 Kubernetes、CSI controller/node、StorageClass、节点数及实际实现版本。默认 kind 存储不自动等于 CSI。须先核实指定 StorageClass 的 `provisioner` 是目标 CSI 驱动、支持动态卷、RWO 与非 root 写入；没有对应能力就停止，而不是强行替换成 hostPath 或共享 PVC。要做跨节点验证，还须有**两个真实满足驱动拓扑的节点**；否则第三阶段保持 `NOT_RUN`。本篇只读测试不与写入 Pod 同时挂载，避免把多节点占用冲突当作只读拒绝。

从同篇目录执行以下命令；保留证据目录路径，清理清单只限本篇创建的对象。镜像需按 13 的步骤由共用包的 `probe_app.py` 与 `Dockerfile.single` 构建并推送到节点能访问的仓库，以实际 manifest digest 填入；包的完整性和运行结果分别验证。

```sh
set -eu
sha256sum -c CHECKSUMS.sha256 C30_CHECKSUMS.sha256
OWN_NAMESPACE=c30-dedicated
: "${CSI_CLASS:?填入专用 CSI StorageClass 名称}"
: "${PROBE_IMAGE:?填入已推送镜像的 manifest digest}"
printf '%s\n' "$CSI_CLASS" | grep -Eq '^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$'
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
kubectl get storageclass "$CSI_CLASS" -o yaml
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-30-evidence.XXXXXX)
date -u +%FT%TZ | tee "$OWN_EVIDENCE/start-utc.txt"
sed -e "s|REPLACE_WITH_CSI_CLASS|$CSI_CLASS|g" -e "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c30-storage.yaml > "$OWN_EVIDENCE/storage.yaml"
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c30-readonly.yaml > "$OWN_EVIDENCE/readonly.yaml"
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/storage.yaml"
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c30-writer --timeout=180s
```

`set -e` 中途失败时仍要执行文末**本篇限定**清理；若 PVC 一直 Pending，先保存 StorageClass `volumeBindingMode`、Pod 调度事件和 CSI controller 日志，不用创建同名第二个 PVC 掩盖失败。`CSI_CLASS` 中若有不安全替换字符或是共享类，先在专用 VM 人工核验替换文件；不直接复制别人提供的存储类到自己的命名空间。

## 先定位卷再发送单次请求

持久化测试只写合成内容，不含生产秘密。`kubectl exec` 取容器内 mountinfo 和路径所有权时指定真实容器；CSI 调用日志由 VM 管理者在对应 node 插件上采集，不在共享节点随意遍历宿主路径。下述端口转发仅供独立终端的请求使用；示例在 Pod 中请求回环，以免依赖端口转发是否还在后台。

```sh
kubectl -n "$OWN_NAMESPACE" get pvc c30-state -o yaml > "$OWN_EVIDENCE/pvc-before.yaml"
OWN_PV=$(kubectl -n "$OWN_NAMESPACE" get pvc c30-state -o jsonpath='{.spec.volumeName}')
test -n "$OWN_PV"
kubectl get pv "$OWN_PV" -o yaml > "$OWN_EVIDENCE/pv-before.yaml"
kubectl -n "$OWN_NAMESPACE" get pod c30-writer -o json > "$OWN_EVIDENCE/pod-before.json"
kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- cat /proc/self/mountinfo > "$OWN_EVIDENCE/mountinfo-before.txt"
kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- python3 -c 'import os; print(os.stat("/var/lib/probe")); print(os.readlink("/proc/self/ns/mnt"))' > "$OWN_EVIDENCE/mount-identity.txt"
kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/identity",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/identity-before.txt"
kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/state",data=b"c30-synthetic-only",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/write.txt"
kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/state",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/read-before.txt"
```

若非 root 写入失败，保留原始客户端退出码、Pod Events、节点 publish 调用与目录属主；`fsGroup` 是否被驱动接受必须实查。不要先修改 PVC 所在节点的全局权限，再把修改后结果充作原方案成功。

## 容器重启和 Pod 重建不是一件事

首次基线成功后，对自有进程发 TERM，观察是否换 containerID 而 Pod UID 保持不变。只有新实例 Ready 后再 GET；也保存失败时的日志和退出码。若专用 VM 禁止发信号，跳过此段并记录权限失败，不得补填预计数据。

```sh
OWN_OLD_CONTAINER=$(kubectl -n "$OWN_NAMESPACE" get pod c30-writer -o jsonpath='{.status.containerStatuses[0].containerID}')
if kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- sh -c 'kill -TERM 1' > "$OWN_EVIDENCE/signal.txt" 2>&1; then
  printf 'signal_exit=0\n' >> "$OWN_EVIDENCE/signal.txt"
else
  printf 'signal_exit=%s\n' "$?" >> "$OWN_EVIDENCE/signal.txt"
fi
OWN_RESTARTED=false
for attempt in $(seq 1 60); do
  OWN_NEW_CONTAINER=$(kubectl -n "$OWN_NAMESPACE" get pod c30-writer -o jsonpath='{.status.containerStatuses[0].containerID}')
  if test -n "$OWN_NEW_CONTAINER" && test "$OWN_OLD_CONTAINER" != "$OWN_NEW_CONTAINER"; then
    OWN_RESTARTED=true
    break
  fi
  sleep 2
done
test "$OWN_RESTARTED" = true || { printf 'restart_not_observed\n' >> "$OWN_EVIDENCE/signal.txt"; exit 1; }
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c30-writer --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pod c30-writer -o json > "$OWN_EVIDENCE/pod-after-restart.json"
kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/state",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/read-after-restart.txt"
kubectl -n "$OWN_NAMESPACE" delete pod c30-writer --wait=true --timeout=180s
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/storage.yaml"
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c30-writer --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pod c30-writer -o json > "$OWN_EVIDENCE/pod-after-recreate.json"
kubectl -n "$OWN_NAMESPACE" exec c30-writer -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/state",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/read-after-recreate.txt"
kubectl -n "$OWN_NAMESPACE" get pvc c30-state -o yaml > "$OWN_EVIDENCE/pvc-after.yaml"
```

`kill` 可能触发立即重启，`wait` 命中旧 Ready 条件时要按 UID、containerID、restartCount 和请求时间重新采样；不强写“已完成容器重启”。Pod 重建的前后 UID 应不同而 PVC/PV UID 相同。换节点不在此脚本自动驱动：先由专用实验环境核查两个节点与存储拓扑、具体 CSI 对 `NodeUnpublishVolume` 和 `NodePublishVolume` 的处理，再给**新** Pod 施加仅限实验节点的调度约束，保存前后 GET、PV UID、挂载及 CSI node 日志。条件不足则保持 `NOT_RUN`，不要修改共享节点标签。

## 隔离只读失败与清理

先删写入 Pod，再创建同一个 PVC 的只读 Pod。Pod Ready 不等于已经证明只读：须先 GET 之前的合成字节，再 POST 同一 `/state` 并捕获非零退出状态、容器日志与 mountinfo。无论客户端看到断连、错误码或请求超时，都只能根据原始证据定位失败层。

```sh
kubectl -n "$OWN_NAMESPACE" delete pod c30-writer --ignore-not-found --wait=true --timeout=180s
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/readonly.yaml"
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c30-readonly --timeout=180s
kubectl -n "$OWN_NAMESPACE" exec c30-readonly -c probe -- cat /proc/self/mountinfo > "$OWN_EVIDENCE/mountinfo-readonly.txt"
kubectl -n "$OWN_NAMESPACE" exec c30-readonly -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/state",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/read-readonly.txt"
if kubectl -n "$OWN_NAMESPACE" exec c30-readonly -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/state",data=b"must-not-write",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/write-readonly.txt" 2>&1; then
  printf 'unexpected_success\n' >> "$OWN_EVIDENCE/write-readonly.txt"
else
  printf 'client_exit=%s\n' "$?" >> "$OWN_EVIDENCE/write-readonly.txt"
fi
kubectl -n "$OWN_NAMESPACE" logs c30-readonly -c probe > "$OWN_EVIDENCE/readonly-logs.txt"
kubectl -n "$OWN_NAMESPACE" get events --sort-by=.lastTimestamp > "$OWN_EVIDENCE/events.txt"
date -u +%FT%TZ | tee "$OWN_EVIDENCE/end-utc.txt"
```

如果只读 Pod 根本没挂上，跳过 HTTP 并记录其事件；不要把 `kubectl wait` 失败写成应用层拒绝。清理前保存本篇 PVC/PV UID、`spec.csi.volumeHandle`、PV reclaim policy 和 CSI 驱动侧状态；`Retain` 的卷不会因为删除 PVC 自动抹除，管理员要按实际 volumeHandle 决定后续回收。

```sh
kubectl -n "$OWN_NAMESPACE" delete pod c30-writer c30-readonly --ignore-not-found --wait=true --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pvc c30-state -o yaml > "$OWN_EVIDENCE/pvc-before-cleanup.yaml"
kubectl get pv "$OWN_PV" -o yaml > "$OWN_EVIDENCE/pv-before-cleanup.yaml"
kubectl -n "$OWN_NAMESPACE" delete pvc c30-state --wait=true --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pod,pvc
kubectl get pv "$OWN_PV" -o yaml > "$OWN_EVIDENCE/pv-after-cleanup.yaml" 2>&1 || true
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=180s
```

只删本篇对象，不清空共享目录、不删除 StorageClass、不手工移除 finalizer；若 CSI 回收失败或 `Retain` 留下数据，保存后台状态并请 VM 管理者处理。云端没有 kind/CSI，以上挂载、写入、重建、只读拒绝和回收全部 `NOT_RUN`；静态页面构建不能充作任何一项的原始实验结果。
