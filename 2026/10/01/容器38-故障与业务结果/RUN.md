# 38 故障范围与恢复验收

仅独立 kind VM 的自建 namespace/卷/节点，先保存 37 的完整成功基线、宿主控制台恢复手段及允许的资源预算。分四轮单独注入：有上限内存申请、终止自建进程、只阻断自建 Pod 网络、停掉专用测试节点；每轮恢复后再进入下一轮。不关闭共享宿主安全机制或默认网络。

```sh
date -u -Iseconds
curl -sS -w 'status=%{http_code} time_total=%{time_total}\n' "$OWN_PROBE_URL/ready"
curl -i "$OWN_PROBE_URL/state"
kubectl -n "$OWN_NAMESPACE" get pods,events -o wide
```

每轮保存原始请求逐条结果、Pod UID/容器 ID/PID、注入起止时间、恢复时刻、数据校验与自有资源清理；Ready 恢复但数据不符仍不算完成。本云端无专用 VM，四类故障全部 `NOT_RUN`。
