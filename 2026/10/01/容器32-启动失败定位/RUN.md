# 32：镜像、入口、只读初始化与探针故障

状态：`NOT_RUN`。仅在独占 kind/CRI VM 与自有 namespace 测试，不删除 registry blob、不改系统镜像仓库、不关安全控制。先固定 Kubernetes、容器运行时、节点架构/系统与真实镜像 digest；正常和四只负例均使用 `imagePullPolicy: Always`。在同篇目录验证通用源码包和两个 YAML 的 SHA，按 13 的步骤用包内 `Dockerfile.single`/`probe_app.py` 构建并推送正常镜像。错误架构需额外固定另一平台镜像，**本篇不提供且不冒充完成**。

## 一次只改变一个变量

先起正常控制 Pod，确认集群能从真实仓库拉取镜像且 probe-app 的 `/identity` 与 `/ready` 成功。镜像替换为同仓库的全零 SHA-256 摘要只是**待验证的预测失败输入**；若正常控制本身也拉取失败，就先保存原始仓库/证书/网络错误，不开展“摘要不存在”的归因。所有对象只在专用 namespace 创建。

```sh
set -eu
sha256sum -c CHECKSUMS.sha256 C32_CHECKSUMS.sha256
OWN_NAMESPACE=c32-dedicated
: "${PROBE_IMAGE:?填入真实镜像 manifest digest}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-32-evidence.XXXXXX)
date -u +%FT%TZ > "$OWN_EVIDENCE/start-utc.txt"
OWN_BAD_IMAGE="${PROBE_IMAGE%@sha256:*}@sha256:$(printf '%064d' 0)"
sed -e "s|REPLACE_WITH_BAD_IMAGE_BY_DIGEST|$OWN_BAD_IMAGE|g" -e "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c32-failures.yaml > "$OWN_EVIDENCE/failures.yaml"
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c32-good.yaml > "$OWN_EVIDENCE/good.yaml"
sed 's|REPLACE_WITH_POD_NAME|c32-control|g' "$OWN_EVIDENCE/good.yaml" > "$OWN_EVIDENCE/control.yaml"
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/control.yaml"
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c32-control --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pod c32-control -o json > "$OWN_EVIDENCE/control.json"
kubectl -n "$OWN_NAMESPACE" exec c32-control -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/identity", timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/control-http.txt"
```

四份负例位于 `c32-failures.yaml` 的四个 YAML 文档，以下脚本按顺序一次只建一个 Pod，先保存事件及容器状态，删除该 Pod，使用同名正常模板修复并验证新 UID 与真实 HTTP，随后才进入下一轮。单次观察窗口限 40 秒，不能由客户端猜测固定报错；`kubectl logs` 对从未成功启动的容器可能不存在，用单独 `.stderr` 保存取不到日志的原因。任何一步失败时 `set -e` 中止，先保存已有证据，再按文末只清理本篇对象。

```sh
OWN_INDEX=1
for pod in c32-pull c32-entry c32-readonly c32-notready; do
  awk -v section="$OWN_INDEX" 'BEGIN {current=1} /^---$/ {current++; next} current==section {print}' "$OWN_EVIDENCE/failures.yaml" > "$OWN_EVIDENCE/$pod-fault.yaml"
  kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/$pod-fault.yaml"
  sleep 10
  kubectl -n "$OWN_NAMESPACE" get pod "$pod" -o json > "$OWN_EVIDENCE/$pod-fault.json"
  kubectl -n "$OWN_NAMESPACE" describe pod "$pod" > "$OWN_EVIDENCE/$pod-describe.txt"
  kubectl -n "$OWN_NAMESPACE" get events --sort-by=.metadata.creationTimestamp > "$OWN_EVIDENCE/$pod-events.txt"
  kubectl -n "$OWN_NAMESPACE" logs "$pod" -c probe --timestamps > "$OWN_EVIDENCE/$pod-logs.txt" 2> "$OWN_EVIDENCE/$pod-logs.stderr" || true
  if test "$pod" = c32-notready; then
    kubectl -n "$OWN_NAMESPACE" exec "$pod" -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/identity",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/$pod-direct.txt"
  fi
  OWN_FAULT_UID=$(kubectl -n "$OWN_NAMESPACE" get pod "$pod" -o jsonpath='{.metadata.uid}')
  kubectl -n "$OWN_NAMESPACE" delete pod "$pod" --wait=true --timeout=180s
  sed "s|REPLACE_WITH_POD_NAME|$pod|g" "$OWN_EVIDENCE/good.yaml" > "$OWN_EVIDENCE/$pod-repaired.yaml"
  kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/$pod-repaired.yaml"
  kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready "pod/$pod" --timeout=180s
  OWN_FIXED_UID=$(kubectl -n "$OWN_NAMESPACE" get pod "$pod" -o jsonpath='{.metadata.uid}')
  test -n "$OWN_FAULT_UID" && test -n "$OWN_FIXED_UID" && test "$OWN_FAULT_UID" != "$OWN_FIXED_UID"
  kubectl -n "$OWN_NAMESPACE" get pod "$pod" -o json > "$OWN_EVIDENCE/$pod-repaired.json"
  kubectl -n "$OWN_NAMESPACE" exec "$pod" -c probe -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:18080/identity",timeout=3); print(r.status,r.read().decode())' > "$OWN_EVIDENCE/$pod-repaired-http.txt"
  kubectl -n "$OWN_NAMESPACE" delete pod "$pod" --wait=true --timeout=180s
  OWN_INDEX=$((OWN_INDEX+1))
done
date -u +%FT%TZ > "$OWN_EVIDENCE/end-utc.txt"
```

十秒不足以观察镜像退避或探针状态时，按上限 40 秒重新采样同一 Pod UID 的对象和事件，不把未观察到的异常补写进去。对 `c32-notready` 正常的直连 200 与 Ready=false 要分别保存；其它三例若其实已经发生其它更早失败，当前负例不成立，停止并排查 VM 条件。镜像错误的拉取退避需记录节点/运行时原始错误，Pod 事件本身不足以区分 404、鉴权和网络故障。固定平台的错误 ELF 需要单独有权验证的制品，不能用 `c32-entry` 伪造。

## 清理本篇对象

```sh
kubectl -n "$OWN_NAMESPACE" get pods -o json > "$OWN_EVIDENCE/pods-before-cleanup.json"
kubectl -n "$OWN_NAMESPACE" delete pod c32-control c32-pull c32-entry c32-readonly c32-notready --ignore-not-found --wait=true --timeout=180s
kubectl -n "$OWN_NAMESPACE" get pods
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=180s
```

不删除 registry、镜像缓存或其它任务对象。当前无 kind/Docker/containerd/专用 registry，四类故障与修复均 `NOT_RUN`，YAML/脚本的静态校验不能当作第一条错误或修复结果。
