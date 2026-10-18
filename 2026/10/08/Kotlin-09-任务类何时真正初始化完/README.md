# Kotlin 09 素材与独立复跑

`task-initialization.svg` 对照构造、setter 与首次 lazy 读取的时间点。`kotlin-language-09.tar.gz` 含 Wrapper、完整累计工程、RUN/VERSIONS 和 00–09 的研究及原始实验记录，旁边的 `.sha256` 校验下载字节。

```bash
sha256sum -c kotlin-language-09.tar.gz.sha256
mkdir -p /tmp/kotlin-09-replay
tar -xzf kotlin-language-09.tar.gz -C /tmp/kotlin-09-replay
cd /tmp/kotlin-09-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线命令要求本机 JDK 21 与依赖缓存。派生类的危险反例只在 `TaskTest` 中，不要拿来替换正常 Task 的构造方式；Task 目前不由 CLI 创建，不执行后台任务，也不持久化。
