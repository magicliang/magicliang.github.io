# Kotlin 37 性能实验素材

`workload-and-measurement.svg` 标出各组输入与不同成本归因。JMH 1.37 / JDK 21 的数值保留在 `writing-plans/kotlin/verification/37/jmh-results.json`；跨主机、不同 JVM 或不同输入不应复用这些均值。

```bash
sha256sum -c kotlin-language-37.tar.gz.sha256
mkdir -p /tmp/kotlin-37-replay
tar -xzf kotlin-language-37.tar.gz -C /tmp/kotlin-37-replay
cd /tmp/kotlin-37-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test loopbackTest jmh
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

非法 CLI `./gradlew --offline --no-daemon --console=plain run --args=submit` 预期退出非零。须具备 JMH 与既有 Gradle 依赖缓存、PostgreSQL 16 二进制；数据库测试自建隔离临时集群，不读系统默认数据库。真实 HTTP/数据库性能与公网部署均 NOT_RUN。
