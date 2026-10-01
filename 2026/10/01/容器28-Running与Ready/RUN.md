# 28 探针与真实端点

在独立 kind 集群，使用同一 probe-app digest，让容器参数包含 `--ready-delay 10`；按所选 Kubernetes 版本明确 startup/readiness/liveness、init/sidecar 的实际配置。校验包摘要再创建仅属于自己的 Deployment 与 Service。

```sh
kubectl -n "$OWN_NAMESPACE" get pod -o wide
kubectl -n "$OWN_NAMESPACE" get endpointslices -o wide
kubectl -n "$OWN_NAMESPACE" get events --sort-by=.metadata.creationTimestamp
curl -i "$OWN_PROBE_URL/ready"
```

每轮记录 UTC、Pod UID、容器 ID、Pod phase、探针返回、EndpointSlice 与请求结果；坏版本滚动更新只操作实验 Deployment，清理时核对 Pod/Service 无残留。当前无 kind，`NOT_RUN`。
