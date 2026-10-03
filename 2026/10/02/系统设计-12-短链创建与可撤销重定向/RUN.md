# 第 12 篇复现实验

权威源码：`examples/system-design/labs/12/shortlink.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：12 个 SQLite 独立连接竞争同一短码及撤销门禁。

```bash
python3 examples/system-design/labs/12/shortlink.py
python3 examples/system-design/labs/12/shortlink.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：created=1、conflicts=11、rows=1；revoked_safe=null；旧缓存反例被拒绝。

证据：`examples/system-design/evidence/12/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：缓存字典与顺序撤销模型；未运行 HTTP、浏览器、CDN、多主数据库。
