# Kotlin 08 素材与独立复跑

`eager-vs-sequence.svg` 呈现同一标签变换的调用轨迹。`kotlin-language-08.tar.gz` 包含完整累计工程、Wrapper、RUN/VERSIONS 与 00–08 的研究和原始实验记录；同名 `.sha256` 校验压缩包。

```bash
sha256sum -c kotlin-language-08.tar.gz.sha256
mkdir -p /tmp/kotlin-08-replay
tar -xzf kotlin-language-08.tar.gz -C /tmp/kotlin-08-replay
cd /tmp/kotlin-08-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线运行需要 JDK 21 和已缓存依赖；没有缓存时先取得依赖，不得把依赖解析失败记成 Sequence 行为失败。08 没有测性能、线程、HTTP 或数据库。
