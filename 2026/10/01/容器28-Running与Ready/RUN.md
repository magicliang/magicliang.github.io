# 28：Pod 阶段、探针、端点和请求

状态：`NOT_RUN`。只在独立 kind VM；先在本篇同名目录校验 `CHECKSUMS.sha256` 与 `C28_CHECKSUMS.sha256`，解压共用包，按 13/26 的镜像步骤构建、推送 probe-app，并取得可从 kind 节点拉取的 manifest digest。记录实际 kind/Kubernetes/containerd/CNI/镜像版本；`c28-rollout.yaml` 与 `c28-bad-readiness.yaml` 都是本篇独立附件，后者仅为 `kubectl patch --type=strategic` 的受控片段，不可单独作为 Pod 创建。未在这台共享云端执行任何命令或构建镜像。

## 限制对象和正常路径

`c28-rollout.yaml` 创建一副本 Deployment 与 ClusterIP Service，应用仍是 `probe_app.py`，`--ready-delay 10`（该脚本限制在 0..30 秒）。普通 init 容器最多休眠两秒，Pod 在此期间无应用进程；startup、readiness 和 liveness 分别请求 `/health`、`/ready`、`/health`。只在新建的专用 namespace 操作；先核对同名空间不存在，创建返回成功才能在收尾时删掉它。Service 请求需专用集群内的客户端，不能用本机 `127.0.0.1` 假装访问到 Pod。

```sh
set -eu
OWN_NAMESPACE=c28-dedicated
: "${PROBE_IMAGE:?填写已推送的真实 manifest digest 引用}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-28-evidence.XXXXXX)
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c28-rollout.yaml > "$OWN_EVIDENCE/rollout.yaml"
date -u +%FT%TZ
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/rollout.yaml"
kubectl -n "$OWN_NAMESPACE" get pods -o json > "$OWN_EVIDENCE/pods-created.json"
kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c28-probe -o json > "$OWN_EVIDENCE/slices-created.json"
for attempt in $(seq 1 15); do
  date -u +%FT%TZ >> "$OWN_EVIDENCE/progress-timeline.txt"
  kubectl -n "$OWN_NAMESPACE" get pods -o json >> "$OWN_EVIDENCE/progress-timeline.txt"
  kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c28-probe -o json >> "$OWN_EVIDENCE/progress-timeline.txt"
  sleep 2
done
```

从创建时起每两秒有界采样（建议 30 秒），保留 Pod UID、`.status.phase`、init 状态、containerID/`ready`、Pod Ready condition、EndpointSlice 中对应地址的 `conditions.ready`/`terminating` 与事件；不能只保存结束时一份成功状态。如果 Pod 因镜像/网络失败没有 Running，保存错误并停止，不把它归因为 readiness 503。正常期另从 Pod 内请求 `/ready`/`/identity`，与 Service 入口请求分开记录；每个请求记录 UTC、状态/异常、Pod UID 和源位置。以下是只读采样和就绪检查示例：

```sh
kubectl -n "$OWN_NAMESPACE" get pods -o wide
kubectl -n "$OWN_NAMESPACE" get pods -o json > "$OWN_EVIDENCE/pods-progress.json"
kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c28-probe -o json > "$OWN_EVIDENCE/slices-progress.json"
kubectl -n "$OWN_NAMESPACE" get events --sort-by=.metadata.creationTimestamp > "$OWN_EVIDENCE/events-progress.txt"
kubectl -n "$OWN_NAMESPACE" rollout status deployment/c28-probe --timeout=120s
kubectl -n "$OWN_NAMESPACE" get pods -o json > "$OWN_EVIDENCE/pods-ready.json"
kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c28-probe -o json > "$OWN_EVIDENCE/slices-ready.json"
```

若请求期需要服务端视角，另在本篇命名空间创建一只短命的 Python 客户端 Pod（仍用相同镜像 digest），请求 `http://c28-probe:18080/identity`；脚本最多循环 15 次、间隔 2 秒，记录每次状态或异常，并保留客户端 Pod UID/日志与实际返回码。不要把 Pod 内 `localhost` 的 200 算成 Service 可用：

```sh
kubectl -n "$OWN_NAMESPACE" run c28-client --restart=Never --image="$PROBE_IMAGE" --command -- python3 -u -c '
import datetime
import time
import urllib.request
for attempt in range(15):
    try:
        with urllib.request.urlopen("http://c28-probe:18080/identity", timeout=2) as response:
            result = f"http={response.status} body={response.read(512)!r}"
    except Exception as error:
        result = f"error={type(error).__name__}:{error}"
    print(datetime.datetime.now(datetime.timezone.utc).isoformat(), attempt, result, flush=True)
    time.sleep(2)
'
kubectl -n "$OWN_NAMESPACE" get pod c28-client -o json > "$OWN_EVIDENCE/client.json"
kubectl -n "$OWN_NAMESPACE" logs c28-client --timestamps > "$OWN_EVIDENCE/client.log"
```

若客户端尚未运行就取 logs，真实命令可报错并让 `set -e` 退出；重试应先看 `client.json`，保留所有失败返回码，不能伪造成功请求。该脚本从无上限网络调用变成最多 15 次×2 秒，每次响应最多读 512 字节，不承担 in-flight 慢请求验证。

## 坏就绪配置与回退

先保存旧 Pod UID、Deployment revision/ReplicaSet 集合与可用端点。然后仅对本篇 Deployment 使用战略合并补丁，把**新模板**的 readiness 路径改为 `probe_app.py` 未提供的路径；镜像 digest 保持不变，所以这是坏配置而不是新镜像二进制。`maxSurge: 1`/`maxUnavailable: 0` 在有节点余量的前提下允许先建新 Pod，坏版本长期不 Ready 时旧 Pod 应保留；不能在没有实际 Pod 事件时直接声称滚动更新卡在 probe。预期 `rollout status --timeout` 可能非零，须捕获实际退出码，不能让 shell 的 `set -e` 中断清理。

```sh
kubectl -n "$OWN_NAMESPACE" get deployment c28-probe -o json > "$OWN_EVIDENCE/deploy-before-bad.json"
kubectl -n "$OWN_NAMESPACE" get replicasets,pods -o wide > "$OWN_EVIDENCE/replicas-before-bad.txt"
kubectl -n "$OWN_NAMESPACE" patch deployment c28-probe --type=strategic --patch-file c28-bad-readiness.yaml
if kubectl -n "$OWN_NAMESPACE" rollout status deployment/c28-probe --timeout=60s; then
  printf 'bad_rollout_status=0\n' > "$OWN_EVIDENCE/bad-rollout-result.txt"
else
  printf 'bad_rollout_status=%s\n' "$?" > "$OWN_EVIDENCE/bad-rollout-result.txt"
fi
kubectl -n "$OWN_NAMESPACE" get deployment,replicasets,pods -o wide > "$OWN_EVIDENCE/bad-rollout-objects.txt"
kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c28-probe -o json > "$OWN_EVIDENCE/bad-slices.json"
kubectl -n "$OWN_NAMESPACE" get events --sort-by=.metadata.creationTimestamp > "$OWN_EVIDENCE/bad-events.txt"
kubectl -n "$OWN_NAMESPACE" run c28-bad-client --restart=Never --image="$PROBE_IMAGE" --command -- python3 -u -c '
import datetime
import time
import urllib.request
for attempt in range(10):
    try:
        with urllib.request.urlopen("http://c28-probe:18080/identity", timeout=2) as response:
            result = f"http={response.status} body={response.read(512)!r}"
    except Exception as error:
        result = f"error={type(error).__name__}:{error}"
    print(datetime.datetime.now(datetime.timezone.utc).isoformat(), attempt, result, flush=True)
    time.sleep(2)
'
kubectl -n "$OWN_NAMESPACE" get pod c28-bad-client -o json > "$OWN_EVIDENCE/bad-client.json"
kubectl -n "$OWN_NAMESPACE" logs c28-bad-client --timestamps > "$OWN_EVIDENCE/bad-client.log"
kubectl -n "$OWN_NAMESPACE" patch deployment c28-probe --type=strategic --patch '{"spec":{"template":{"spec":{"containers":[{"name":"probe","readinessProbe":{"httpGet":{"path":"/ready","port":18080}}}]}}}}'
kubectl -n "$OWN_NAMESPACE" rollout status deployment/c28-probe --timeout=120s
```

比较坏配置前后旧 Pod UID、新 Pod UID、ReplicaSet、各 EndpointSlice 的 ready/terminating、服务请求实际响应及修复后的回归。若由于容量不足新 Pod Pending，该分支应改查调度而不是宣称 readiness 探针拒绝；如果旧 Pod 已因其它原因不可用，也不把失败请求全算作此补丁所致。

## 终止、在途处理与清理边界

删除专用 Deployment 的 Pod 前，先记录当前 Service 请求及 Pod UID，再用有上限的端点 watch、短时客户端采样与 `kubectl get events` 追踪 EndpointSlice 变化；确认删掉的 UID 确属本篇，不改其它 namespace。`probe_app.py` 已注册 SIGTERM/SIGINT 处理器，停止标志阻止继续处理新接入请求；主线程先启动三秒定时器，再调用 `server.shutdown()`。定时器到期时关闭仍在处理的连接，提前结束则取消定时器。其单线程 HTTP 请求处理尚无人工慢请求端点；上面的短请求可能看见断连或成功，但不能据此声称“所有在途请求已优雅完成”。要验收长在途请求，应增加受控慢请求与请求时间线记录、重建 digest 后另做实验；已有终止处理不能替代真实节点结果，该项维持 `NOT_RUN`。`signal_probe.py` 只有信号日志而无 HTTP，不可替代真实流量。

从 `kubectl -n "$OWN_NAMESPACE" get pods -l app=c28-probe -o wide` 手工选一只当前确认属于本篇 Deployment 的 Pod，并核对其 owner 与 UID 后设置 `OWN_POD_TO_TERMINATE`；以下命令只删除这只 Pod，Deployment 会补建新实例。记录请求时需要另在专用客户端并行执行上面的有界 Service 请求，避免把单纯的控制面变化当成业务结果：

```sh
: "${OWN_POD_TO_TERMINATE:?先核对本篇 Pod owner 与 UID}"
kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD_TO_TERMINATE" -o json > "$OWN_EVIDENCE/terminating-before.json"
kubectl -n "$OWN_NAMESPACE" delete pod "$OWN_POD_TO_TERMINATE" --wait=false
for attempt in $(seq 1 10); do
  date -u +%FT%TZ >> "$OWN_EVIDENCE/terminating-timeline.txt"
  kubectl -n "$OWN_NAMESPACE" get pods -l app=c28-probe -o json >> "$OWN_EVIDENCE/terminating-timeline.txt"
  kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c28-probe -o json >> "$OWN_EVIDENCE/terminating-timeline.txt"
  sleep 2
done
```

清理前保存 Pod/ReplicaSet/EndpointSlice 的最后 JSON、客户端原始日志、Pod 事件和操作的退出码。仅在本轮成功创建命名空间的前提下删除专用对象并核对残留：

```sh
kubectl -n "$OWN_NAMESPACE" delete deployment c28-probe --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" delete service c28-probe --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" delete pod c28-client --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" delete pod c28-bad-client --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" get deployment,service,pods,endpointslices
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=120s
```

不把状态重置为“已验收”：本机无 kind/CRI，无真实 Pod/Service 请求、终止观察或滚动更新原始记录，完整实验 `NOT_RUN`；同篇模板、源码与命令只能静态检验。
