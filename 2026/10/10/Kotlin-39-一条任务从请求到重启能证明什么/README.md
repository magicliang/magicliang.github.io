# Kotlin 39 最终主线素材

`end-to-end-ownership.svg` 只标真实跑通的本机 JSON→HTTP→Job→JDBC 路径与事务/任务完成点。下载 ZIP 有两个入口（CLI 与回环 HTTP），HTTP 若不设置显式 `TASK_DB_URL` 则只使用内存；**不得**把返回 202 当任务可靠持久化的证明。

```bash
sha256sum -c kotlin-language-39.tar.gz.sha256
sha256sum -c kotlin-task-service-39.zip.sha256
mkdir -p /tmp/kotlin-39-replay
tar -xzf kotlin-language-39.tar.gz -C /tmp/kotlin-39-replay
cd /tmp/kotlin-39-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test loopbackTest packageTest distZip jmh
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

非法 CLI `./gradlew --offline --no-daemon --console=plain run --args=submit` 预期非零退出。测试要使用 JDK 21、PostgreSQL 16 二进制、缓存 JMH 1.37/其他依赖；JUnit fixture 自动启停自己的临时数据库，URL 只传给自己启动的子进程，不连接默认集群。真实网络中途断线、无终态任务恢复及生产数据库发布仍 NOT_RUN。
