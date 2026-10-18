# Kotlin 14 素材复跑

`static-extension-dispatch.svg` 展示同一 `Failed` 对象在不同静态接收者类型下调用扩展的选择；`kotlin-language-14.tar.gz` 含 Wrapper、RUN/VERSIONS、完整累计工程及 00–14 的研究与原始测试结果。

```bash
sha256sum -c kotlin-language-14.tar.gz.sha256
mkdir -p /tmp/kotlin-14-replay
tar -xzf kotlin-language-14.tar.gz -C /tmp/kotlin-14-replay
cd /tmp/kotlin-14-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线命令需要 JDK 21 与已缓存依赖。旧 CLI 尚未使用 `formatTaskState`；图表与单元测试也不证明并发下的任务状态可靠性。
