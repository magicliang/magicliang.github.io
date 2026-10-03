# 第 14 篇复现实验

权威源码：`examples/system-design/labs/14/upload.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：上传成功而元数据事务失败后隐藏与恢复。

```bash
python3 examples/system-design/labs/14/upload.py
python3 examples/system-design/labs/14/upload.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：after_failure_visible=[]；removed=[orphan]；待完成会话对象保留；重试后仅 p1 可见。

证据：`examples/system-design/evidence/14/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：文件是标记字节；未验证图片解码、缩略图、云 API 或并发 GC 互斥。
