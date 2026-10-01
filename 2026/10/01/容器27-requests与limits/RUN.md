# 27 四种资源失败分层

独立 kind VM：先固定 kubelet、cgroup v2、资源可分配量和探针镜像 digest，并校验本目录包。`bounded_load.py` 在代码层限制计算至 2 秒、显式分配至多 32 MiB；OOM/节点压力只在专用环境注入，需控制台恢复预案。

```sh
kubectl -n "$OWN_NAMESPACE" describe pod "$OWN_POD"
kubectl -n "$OWN_NAMESPACE" get events --sort-by=.metadata.creationTimestamp
cat "$OWN_POD_CGROUP/cpu.stat" "$OWN_POD_CGROUP/memory.events"
```

对调度等待、CPU 节流、内存限制事件、节点驱逐分别保存 UID/容器 ID/PID、cgroup 计数前后、事件、退出与清理。共享环境是 v1 只读，无 kind，全部 `NOT_RUN`。
