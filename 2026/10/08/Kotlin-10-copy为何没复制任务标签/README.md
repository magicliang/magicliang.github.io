# Kotlin 10 素材与独立复跑

`record-copy.svg` 是 TaskRecord 外层复制与内部标签列表共享引用的图。`kotlin-language-10.tar.gz` 含 Wrapper、完整累计工程、RUN/VERSIONS 及 00–10 的研究与原始实验输出；同名 `.sha256` 文件核验压缩包。

```bash
sha256sum -c kotlin-language-10.tar.gz.sha256
mkdir -p /tmp/kotlin-10-replay
tar -xzf kotlin-language-10.tar.gz -C /tmp/kotlin-10-replay
cd /tmp/kotlin-10-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

需要 JDK 21 和可离线使用的依赖缓存；材料中的可变标签键是故意保留的失败示例，不建议用作真实任务的可变索引。没有真实数据库或服务请求。
