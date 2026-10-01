# 30 PVC、CSI 和应用路径

专用 kind VM，固定 CSI 驱动/存储类别/访问模式及实际源码版本。校验本目录包后对同一 probe-app 镜像做自有 PVC/Pod，写入限定大小的合成文本到 `/state`：

```sh
kubectl -n "$OWN_NAMESPACE" get pvc,pods -o wide
kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD" -o jsonpath='{.metadata.uid} {.status.containerStatuses[*].containerID}'
kubectl get pv
curl -i -X POST --data 'containers-own-only' "$OWN_PROBE_URL/state"
curl -i "$OWN_PROBE_URL/state"
```

记录 PV、PVC UID、Pod UID、容器 ID、PID、mountinfo、重建各步数据。换节点前确认驱动支持；只读拒绝与数据恢复只在自有卷上测试。删除实验对象前备份原始输出，核对卷清理；云端无 CSI，`NOT_RUN`。
