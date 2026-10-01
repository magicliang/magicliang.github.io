# 34 预先锁定计时边界

独立 VM 固定镜像 digest、CPU 架构、Linux/运行时版本、节点存储与应用参数。冷、热缓存各独立批次，先预设重复次数（例如每组至少 5 次）、并发 1、请求体固定，记录失败数和每轮原始数据。计时点：pull 开始/结束、解包完成、snapshot 准备、OCI create/start、应用首日志、首次 `/ready=200`；保存同一容器 ID 的可关联事件，不混用不同宿主的未同步时钟。

```sh
date -u -Iseconds
curl -sS -w 'status=%{http_code} time_total=%{time_total}\n' "$OWN_PROBE_URL/ready"
```

只在自有镜像/缓存环境控制冷热，不清理共享宿主全局缓存。本机没有镜像运行时与可核对事件，所有时间数据 `NOT_RUN`。
