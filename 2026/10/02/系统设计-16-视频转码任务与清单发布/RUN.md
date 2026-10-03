# 第 16 篇复现实验

权威源码：`examples/system-design/labs/16/video.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：任务重试去重、缺段和损坏拒绝发布、完整发布与 HTTP 引用。

```bash
python3 examples/system-design/labs/16/video.py
python3 examples/system-design/labs/16/video.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：task_rows=3、releases=1；缺段/损坏阶段无清单或发布行；HTTP 获取三段字节相等，删除第二段后 404。

证据：`examples/system-design/evidence/16/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：分段为 PROTOCOL-FIXTURE，不可解码；播放、ABR、CDN 性能未测试。正文缓冲和带宽为算术预算。
