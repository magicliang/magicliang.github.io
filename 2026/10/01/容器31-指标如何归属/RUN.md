# 31 一次请求的多层样本

专用 VM 固定进程、容器、节点与探针版本，校验包并记录相同输入。对同一 Pod UID/容器 ID/PID，保存至少两组明确间隔的 HTTP 响应时间与 `cpu.stat`、`memory.events`、`io.stat` 前后值：

```sh
date -u -Iseconds
curl -sS -w 'status=%{http_code} time_total=%{time_total}\n' "$OWN_PROBE_URL/ready"
cat "$OWN_POD_CGROUP/cpu.stat" "$OWN_POD_CGROUP/memory.events" "$OWN_POD_CGROUP/io.stat"
```

任务迁移/重建后重新解析 PID 和 cgroup。报告采样间隔和缺失数据，不把普通进程 00 的记录当容器指标；本机 cgroup v1 只读，`NOT_RUN`。
