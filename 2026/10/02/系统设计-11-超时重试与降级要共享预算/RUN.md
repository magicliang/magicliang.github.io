# 第 11 篇复现实验

权威源码：`examples/system-design/labs/11/retry.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：虚拟时间多层重试、慢下游、总预算和准入。

```bash
python3 examples/system-design/labs/11/retry.py
python3 examples/system-design/labs/11/retry.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：900 次无保护调用；保护后 40 次、拒绝 80、最长虚拟 220 ms；150 ms 总预算下 20 次。

证据：`examples/system-design/evidence/11/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：虚拟时钟与固定突发，不是网络、连接池或生产限流性能测试。
