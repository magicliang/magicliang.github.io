# 35 固定实验变量

独立 Linux VM，先确认相同程序字节、架构、输入、CPU 亲和性、cgroup 配额、文件系统和网络路径。`bounded_load.py --seconds 1 --memory-mib 8` 为有界负载；对普通进程与自建容器分别预设预热、重复次数（例如每组至少 10 次）、并发、失败率。每轮记录原始吞吐/请求延迟与 CPU/memory/io 计数，而不是填估算百分比。

```sh
python3 bounded_load.py --seconds 1 --memory-mib 8
curl -sS -w 'status=%{http_code} time_total=%{time_total}\n' "$OWN_PROBE_URL/ready"
```

文件系统与网络实验另外锁定设备/缓存/接口/封装与抓包。只改一个条件后比较分位数和失败数；当前只有普通进程、缺容器和双 VM，完整对照 `NOT_RUN`。
