# 第 13 篇复现实验

权威源码：`examples/system-design/labs/13/paste.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：整数时间到期边界、撤销拒绝及延后清理。

```bash
python3 examples/system-design/labs/13/paste.py
python3 examples/system-design/labs/13/paste.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：expiry_boundary_denied、wrong_owner_denied、revoked_denied 为 true；清理前正文存在；清理后正文、索引、缓存均空。

证据：`examples/system-design/evidence/13/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：未验证跨机时钟、云对象、备份清理、密钥销毁；unlink 不等于磁盘字节不可恢复。
