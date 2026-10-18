# Kotlin 35 素材与数据库复跑

`jdbc-transaction-boundaries.svg` 区分独立数据库连接、同一同步事务与协程外侧返回。归档包括完整累计工程、Gradle Wrapper、`VERSIONS.md`、历史研究与原始测试输出。

```bash
sha256sum -c kotlin-language-35.tar.gz.sha256
mkdir -p /tmp/kotlin-35-replay
tar -xzf kotlin-language-35.tar.gz -C /tmp/kotlin-35-replay
cd /tmp/kotlin-35-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test loopbackTest
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

非法 CLI `./gradlew --offline --no-daemon --console=plain run --args=submit` 预期非零退出。必须在同版本依赖缓存与本机 PostgreSQL 16 二进制可用的前提下运行；测试自动启动并销毁自己的临时数据库，不接入默认集群，不需要公共数据库凭据。数据库驱动取消单独断言，协程取消如何影响所有同步查询仍 NOT_RUN。
