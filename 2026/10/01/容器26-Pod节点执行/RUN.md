# 26 由 Pod UID 追到进程

只在独立 kind 实验 VM；先核对 `CHECKSUMS.sha256` 再解压源码包，用 13 的 Dockerfile 构建完整镜像并记录真实 digest。固定 kind/Kubernetes/containerd/CNI 版本及对应源码 tag/commit，不能从滚动文档推断本机 shim 数量。运行自己命名空间下的 probe-app：

```sh
kubectl -n "$OWN_NAMESPACE" get pod "$OWN_POD" -o jsonpath='{.metadata.uid} {.status.containerStatuses[*].containerID}'
crictl pods --name "$OWN_POD"
crictl ps -a
crictl inspect "$OWN_CONTAINER_ID"
```

从 Pod UID、sandbox ID、容器 ID 到宿主 PID、ns inode、cgroup、镜像 digest 做一行关联；同名重建时复查值，删除只属于实验的 Pod/namespace 并核对对象清理。当前无 kind/CRI，全部 `NOT_RUN`。
