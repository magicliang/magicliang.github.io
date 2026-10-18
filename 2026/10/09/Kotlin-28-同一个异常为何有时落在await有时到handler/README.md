# Kotlin 28 素材与复跑

`coroutine-failure-topologies.svg` 区分父级策略、错误观察位置和兄弟任务退出路径。`kotlin-language-28.tar.gz` 为完整累计工程、Wrapper、RUN/VERSIONS、来源与原始验证输出的快照；不表示网站已部署。

```bash
sha256sum -c kotlin-language-28.tar.gz.sha256
mkdir -p /tmp/kotlin-28-replay
tar -xzf kotlin-language-28.tar.gz -C /tmp/kotlin-28-replay
cd /tmp/kotlin-28-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线命令要求精确版本依赖缓存。`verification/28/` 有实际 Gradle 和逐组 JUnit 退出码；本篇未运行真实网络或数据库，也未验证遗漏 `Deferred.await()` 的服务级告警策略。
