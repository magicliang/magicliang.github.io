# 第 18 篇复现实验

权威源码：`examples/system-design/labs/18/timeline.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：固定普通/热点作者负载下对照推拉混合与游标分页。

```bash
python3 examples/system-design/labs/18/timeline.py
python3 examples/system-design/labs/18/timeline.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：三策略 feeds 完全相同；写引用 2020/0/20；候选数均 14；两页无交集；全推超过 100 份预算反例退出 2。

证据：`examples/system-design/evidence/18/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：纯操作数模型，未运行 Redis、队列或真实延迟压测；不能推导全局最优策略。
