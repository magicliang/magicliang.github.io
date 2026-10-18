# Kotlin 38 本地运行与归档

`server-shutdown-order.svg` 表示测试过的停止顺序。正文中的 task-server 发行包是本地 Gradle `distZip` 的产物，包含两个启动脚本（原 CLI 与回环服务），**不是部署产物**。

```bash
sha256sum -c kotlin-language-38.tar.gz.sha256
sha256sum -c kotlin-task-server-38.zip.sha256
mkdir -p /tmp/kotlin-38-replay
tar -xzf kotlin-language-38.tar.gz -C /tmp/kotlin-38-replay
cd /tmp/kotlin-38-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test loopbackTest packageTest distZip jmh
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

非法 CLI `./gradlew --offline --no-daemon --console=plain run --args=submit` 应非零退出。回环服务启动需带 1–65535 端口；包测试会启停独立 JVM，数据库回归用本机 PostgreSQL 16 二进制启动独立临时集群，JMH 1.37 依赖须预先缓存。真实部署/外网流量与 HTTP+JDBC 串接均 NOT_RUN。
