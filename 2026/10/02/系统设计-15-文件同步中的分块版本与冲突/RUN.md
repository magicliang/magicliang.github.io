# 第 15 篇复现实验

权威源码：`examples/system-design/labs/15/sync.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：中断续传、校验损坏块、双端旧版本提交及字节恢复。

```bash
python3 examples/system-design/labs/15/sync.py
python3 examples/system-design/labs/15/sync.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：8192 B、8 块、补传 7 块；corruption_detected=true；current_version=2；conflict_device=B；重开元数据库后读回 edit A 与 edit B。

证据：`examples/system-design/evidence/15/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：确定性 CAS 竞争顺序；未验证网络、掉电刷盘、内容定义分块、多目录原子操作。
