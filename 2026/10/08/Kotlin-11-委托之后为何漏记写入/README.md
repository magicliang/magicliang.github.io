# Kotlin 11 素材与独立复跑

`store-delegation.svg` 展示包装器与底层存取对象的两条调用路径。`kotlin-language-11.tar.gz` 包含 Wrapper、完整累计工程、RUN/VERSIONS 和 00–11 的研究/原始实验记录，SHA-256 校验见同名 `.sha256`。

```bash
sha256sum -c kotlin-language-11.tar.gz.sha256
mkdir -p /tmp/kotlin-11-replay
tar -xzf kotlin-language-11.tar.gz -C /tmp/kotlin-11-replay
cd /tmp/kotlin-11-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

需要本机 JDK 21 与依赖缓存。TaskStore 为同步内存实验，`putIfAbsent` 不是多线程原子操作；AuditedTaskStore 的 attempt 日志不是成功持久化记录。旧 CLI 不经过 Store。
