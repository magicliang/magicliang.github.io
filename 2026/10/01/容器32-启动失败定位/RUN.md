# 32 四类故障的最小复现

在专用 VM 的自有镜像/Pod/registry 内分别测试：错误 manifest/blob、不同架构或非法入口、只读或无权限目录、监听 `127.0.0.1` 与非就绪服务。每轮固定 probe-app digest 与单一变更，记录假设、日志、Pod UID、容器 ID、宿主 PID、真实返回、修复和清理。禁止删除共享 registry blob、修改共享网络或关闭安全措施。

```sh
kubectl -n "$OWN_NAMESPACE" describe pod "$OWN_POD"
kubectl -n "$OWN_NAMESPACE" get events --sort-by=.metadata.creationTimestamp
docker inspect "$OWN_CONTAINER_ID"
```

环境可能只有 Docker 或只有 Kubernetes，未提供相应命令时明确 `NOT_RUN`；当前全部缺失，四类注入均 `NOT_RUN`。源码包的本地 OCI 篡改属于 10 的静态实验。
