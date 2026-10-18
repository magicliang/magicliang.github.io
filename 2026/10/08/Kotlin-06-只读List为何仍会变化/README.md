# Kotlin 06 素材与复跑

`query-alias.svg` 是标签视图与结构快照的别名图。`kotlin-language-06.tar.gz` 含完整累计工程、Wrapper、运行说明、版本账本与 00–06 研究/实验原始记录；SHA-256 在同名 `.sha256` 文件里。

```bash
sha256sum -c kotlin-language-06.tar.gz.sha256
mkdir -p /tmp/kotlin-06-replay
tar -xzf kotlin-language-06.tar.gz -C /tmp/kotlin-06-replay
cd /tmp/kotlin-06-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

JDK 21 与已缓存依赖是离线复跑的前提；无缓存时应先解析依赖，不能把下载失败当成集合行为失败。查询结果目前只在 `TaskQueryTest` 中使用，尚无并发、任务存储或 HTTP 查询路径。
