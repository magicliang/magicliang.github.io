# 第 17 篇复现实验

权威源码：`examples/system-design/labs/17/chat.py`。文章附件 `run.py` 与此文件逐字节相同，`run.txt` 是同次执行记录。

场景：持久应用后丢 ACK、重连补齐和客户端去重。

```bash
python3 examples/system-design/labs/17/chat.py
python3 examples/system-design/labs/17/chat.py --unsafe
```

判定：第一条退出 0 且输出 PASS；第二条输出 EXPECTED_REJECTION 并退出 2。二进制可判定观察：重开本地库时 durable_before_lost_ack=[1,2]；投递 [1,2,2,3,4,5]；再次重开展示 [1,2,3,4,5]；服务端唯一消息键拒绝重发。

证据：`examples/system-design/evidence/17/run.json` 保存实际命令、Python、SQLite、平台、源码 SHA-256、预期及实际退出码；同目录 `happy.log`、`negative.log` 为原始 stdout/stderr。文章下载 `run.txt` 包含同一批记录。

边界：无 WebSocket 或客户端 UI；没有多会话、网络乱序和群授权验证；四种确认是正文协议定义。
