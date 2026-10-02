# 29：Pod IP、Service、DNS 与 NetworkPolicy 矩阵

状态：`NOT_RUN`。只在独占 kind VM，由管理者预先固定 Kubernetes/kube-proxy/CNI/策略插件版本和安装来源。要验证 NetworkPolicy，必须**实际安装且验证支持策略的插件**；kind 默认网络或仅有 NetworkPolicy API 对象不等于已强制执行。为策略实验准备插件实现的固定源码定点和对应运行配置，未明确支持/安装时这部分保持 `NOT_RUN`。先在同篇素材目录 `sha256sum -c CHECKSUMS.sha256 C29_CHECKSUMS.sha256`，解压共用 probe-app 源包，按 13 的步骤构建并推送供 kind 节点访问的镜像，填入实际 manifest digest。网络、DNS、iptables/nftables/BPF 路径与 CNI 版本均须读 VM 现场数据，不能从 kube-proxy 的某份源码推断节点一定在用该模式。

## 创建自有对象与直连基线

`c29-workloads.yaml` 创建两个以相同 probe-app 镜像运行、标签相同的后端 Pod、一只 ClusterIP Service 以及两只独立客户端 Pod。客户端也是相同镜像，`kubectl exec` 中调用镜像自带 Python；不要在共享命名空间测试全局默认拒绝。清单镜像字段是故意无法直接运行的占位符，只有替换为真实 digest 才可 `kubectl apply`。

```sh
set -eu
OWN_NAMESPACE=c29-dedicated
: "${PROBE_IMAGE:?填入已推送到专用 registry 的真实 manifest digest}"
printf '%s\n' "$PROBE_IMAGE" | grep -Eq '@sha256:[a-f0-9]{64}$'
! kubectl get namespace "$OWN_NAMESPACE" >/dev/null 2>&1
kubectl create namespace "$OWN_NAMESPACE"
OWN_EVIDENCE=$(mktemp -d /tmp/containers-29-evidence.XXXXXX)
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c29-workloads.yaml > "$OWN_EVIDENCE/workloads.yaml"
date -u +%FT%TZ
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/workloads.yaml"
kubectl -n "$OWN_NAMESPACE" wait --for=condition=Ready pod/c29-backend-a pod/c29-backend-b pod/c29-allowed pod/c29-blocked --timeout=120s
kubectl -n "$OWN_NAMESPACE" get pods,service,endpointslices -o wide > "$OWN_EVIDENCE/baseline-objects.txt"
kubectl -n "$OWN_NAMESPACE" get pods,endpointslices -o json > "$OWN_EVIDENCE/baseline-objects.json"
```

若 Pod 未就绪，先保存事件/CRI/CNI ADD 的失败，不将其归咎于 Service 或策略。检查 Service selector、ClusterIP、两只 Pod 的**真实** IP、UID、containerID 和 EndpointSlice `targetRef.uid`/`conditions.ready`；不能仅凭标签就假定两只 Pod 已进入后端集合。若某 Pod 的 IP 为空，保留 `NOT_RUN` 的直连分支，不填模板中的地址。对每只客户端和每只后端分别执行同一种请求，并在任何策略生效前保存响应：

```sh
OWN_POD_A=$(kubectl -n "$OWN_NAMESPACE" get pod c29-backend-a -o jsonpath='{.status.podIP}')
OWN_POD_B=$(kubectl -n "$OWN_NAMESPACE" get pod c29-backend-b -o jsonpath='{.status.podIP}')
test -n "$OWN_POD_A" && test -n "$OWN_POD_B" && test "$OWN_POD_A" != "$OWN_POD_B"
kubectl -n "$OWN_NAMESPACE" exec c29-allowed -c client -- python3 -c 'import socket; print(socket.getaddrinfo("c29-svc", 18080))' > "$OWN_EVIDENCE/dns-allowed.txt"
for client in c29-allowed c29-blocked; do
  for target in "http://$OWN_POD_A:18080/identity" "http://$OWN_POD_B:18080/identity" "http://c29-svc:18080/identity"; do
    printf 'client=%s target=%s utc=%s\n' "$client" "$target" "$(date -u +%FT%TZ)" >> "$OWN_EVIDENCE/baseline-http.txt"
    kubectl -n "$OWN_NAMESPACE" exec "$client" -c client -- python3 -c 'import sys,urllib.request; r=urllib.request.urlopen(sys.argv[1], timeout=3); print(r.status, r.read(512).decode())' "$target" >> "$OWN_EVIDENCE/baseline-http.txt"
  done
done
```

响应中的 PID 和 network namespace inode 与 A/B 分别直连时的返回进行匹配，才能把 Service 响应归到一个后端。Service 请求多跑几次仅为观察所选后端，**不以轮询次数推断必然均匀负载**；HTTP 连接复用、数据面实现和节点本地流量路由均可影响实际结果。

在进行 NetworkPolicy 实验**之前**，可用第三只临时 Pod 做独立 readiness 负例：同一镜像、同一 selector，`c29-notready.yaml` 只把 readiness 路径指向不存在的 URL。先核对它真正被分配 IP、应用直接 `/identity` 成功而 Pod Ready 仍 false，再读对应 EndpointSlice 的 `targetRef.uid`/ready；控制面变化与客户端实际 Service 请求结果分开保存。它不会改变原有 A/B 的 readiness，切勿记录为“原地让 A 变为未就绪”。删除这只临时 Pod 并核对 EndpointSlice 后再开始策略实验，防止两个故障变量重叠。

```sh
sed "s|REPLACE_WITH_IMAGE_BY_DIGEST|$PROBE_IMAGE|g" c29-notready.yaml > "$OWN_EVIDENCE/notready.yaml"
kubectl -n "$OWN_NAMESPACE" apply -f "$OWN_EVIDENCE/notready.yaml"
sleep 5
kubectl -n "$OWN_NAMESPACE" get pod c29-notready -o json > "$OWN_EVIDENCE/notready-pod.json"
kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c29-svc -o json > "$OWN_EVIDENCE/notready-slices.json"
OWN_NOTREADY_IP=$(kubectl -n "$OWN_NAMESPACE" get pod c29-notready -o jsonpath='{.status.podIP}')
if test -n "$OWN_NOTREADY_IP"; then
  kubectl -n "$OWN_NAMESPACE" exec c29-allowed -c client -- python3 -c 'import sys,urllib.request; r=urllib.request.urlopen(sys.argv[1],timeout=3); print(r.status,r.read(512).decode())' "http://$OWN_NOTREADY_IP:18080/identity" > "$OWN_EVIDENCE/notready-direct.txt"
fi
kubectl -n "$OWN_NAMESPACE" delete pod c29-notready --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c29-svc -o json > "$OWN_EVIDENCE/notready-removed.json"
```

若 5 秒不足以观察状态，按有上限的观察窗口重新采样并记录实际时间；若直连失败或 Pod 没有 IP，不能填“就绪失败但应用可直连”的预期结果。清理收尾阶段对 c29-notready 也需按本篇 UID 检查残留。

## 按行验证策略而非只创建资源

`c29-policies.yaml` 第一条对本篇后端 Pod 选择空 ingress（默认拒绝其余来源），第二条在**同一命名空间**仅允许 `role=c29-allowed` 的客户端访问 TCP 18080。策略是允许规则的并集，作用对象必须是两只后端；客户端的 egress 不受本篇策略约束。先确认当前 CNI/策略插件版本**确实支持 NetworkPolicy**，记录安装插件的配置、policy controller/agent 存活和日志，确认未存在别的影响本篇 namespace 的策略；任一条件不满足就不填写“拒绝通过”。避免在共享集群、系统命名空间或宿主防火墙上直接试验。

期望矩阵仅供预测，**不是**实测输出：`c29-allowed → A/B IP/Service` 均允许，`c29-blocked → A/B IP/Service` 均拒绝或超时（实际错误类型以 VM 记录为准）。DNS 能解析 Service 与后端连通是两回事，插件对 service DNAT 与策略匹配的处理顺序也需按实际实现核对。执行并保存策略前后的同一客户端、同一目的 URL、同一请求上限：

```sh
kubectl -n "$OWN_NAMESPACE" apply -f c29-policies.yaml
kubectl -n "$OWN_NAMESPACE" get networkpolicy -o yaml > "$OWN_EVIDENCE/policy-applied.yaml"
kubectl -n "$OWN_NAMESPACE" get endpointslices -l kubernetes.io/service-name=c29-svc -o json > "$OWN_EVIDENCE/policy-endpoints.json"
for client in c29-allowed c29-blocked; do
  for target in "http://$OWN_POD_A:18080/identity" "http://$OWN_POD_B:18080/identity" "http://c29-svc:18080/identity"; do
    printf 'client=%s target=%s utc=%s\n' "$client" "$target" "$(date -u +%FT%TZ)" >> "$OWN_EVIDENCE/policy-http.txt"
    if kubectl -n "$OWN_NAMESPACE" exec "$client" -c client -- python3 -c 'import sys,urllib.request; r=urllib.request.urlopen(sys.argv[1],timeout=3); print(r.status,r.read(512).decode())' "$target" >> "$OWN_EVIDENCE/policy-http.txt" 2>&1; then
      printf 'exit=0\n' >> "$OWN_EVIDENCE/policy-http.txt"
    else
      printf 'exit=%s\n' "$?" >> "$OWN_EVIDENCE/policy-http.txt"
    fi
  done
done
```

三个来源与目标组合中的 3 秒超时限制单次影响。若 apply 立即成功但规则尚未下发，要记录插件收敛时间、重复同一有界矩阵再判断；无法读到实际插件版本/执行规则时，仅可说 API 中存在配置，不能说策略已强制执行。被拒绝连接通常不会给出应用 HTTP 403，不能在没有原始请求的情况下写固定状态码。

## 回滚、原始证据与清理

先在**本篇命名空间**只删两条具名策略，按相同 URL 复核原来被拒绝的客户端恢复；若仍失败先保存策略 agent/连接跟踪状态，不马上删除其它命名空间对象。保留客户端/Pod UID、直连与 Service 请求结果、DNS 解析、EndpointSlice、实际转发程序/规则、插件源码 tag 与配置、开始/结束 UTC、失败退出码、策略删除结果。

```sh
kubectl -n "$OWN_NAMESPACE" delete networkpolicy c29-deny-other-ingress c29-allow-selected-client --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" exec c29-blocked -c client -- python3 -c 'import urllib.request; r=urllib.request.urlopen("http://c29-svc:18080/identity",timeout=3); print(r.status,r.read(512).decode())' > "$OWN_EVIDENCE/recovered-http.txt"
kubectl -n "$OWN_NAMESPACE" delete pod c29-backend-a c29-backend-b c29-allowed c29-blocked --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" delete pod c29-notready --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" delete service c29-svc --ignore-not-found --wait=true --timeout=120s
kubectl -n "$OWN_NAMESPACE" get pods,service,networkpolicy,endpointslices
kubectl delete namespace "$OWN_NAMESPACE" --wait=true --timeout=120s
```

不删除 kind 节点、默认路由、CNI 插件或其它命名空间的网络策略。无 kind/CRI、无受支持插件，网络四层全 `NOT_RUN`；静态 YAML、网站页面和 checksum 不得改写为真实连通/拒绝证据。
