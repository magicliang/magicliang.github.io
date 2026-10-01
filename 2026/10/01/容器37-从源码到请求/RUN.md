# 37 一次请求的完整证据链

专用 Linux VM + 自建 registry + kind/kubelet + 固定 runtime/CNI/CSI 版本。校验本目录 `CHECKSUMS.sha256` 并解压源码包；固定基础镜像实际 digest 后构建/推送 probe-app，按 digest 部署到自建 namespace。沿“源码包 SHA → manifest digest → Pod UID → sandbox ID → 容器 ID → 宿主 PID → namespace/cgroup → Pod IP/Service → 卷 ID → HTTP 响应”逐项记录原始命令、UTC 时间、退出码和双方对象；缺环节就不能标记全链路成功。

```sh
kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD" -o jsonpath='{.metadata.uid} {.status.containerStatuses[*].containerID}'
curl -i "$OWN_PROBE_URL/identity"
curl -i -X POST --data 'only-my-lab' "$OWN_PROBE_URL/state"
curl -i "$OWN_PROBE_URL/state"
```

同卷重建 Pod 后复读，检查数据内容、挂载源与失败请求；删除自己创建的全部资源并确认清理。云端不含这些运行时，全部 `NOT_RUN`。
