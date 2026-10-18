# Kotlin 17 素材与复跑

`dsl-receiver-scope.svg` 区分任务构造 DSL 内的隐式外层访问与显式 `this@taskDraft`。`kotlin-language-17.tar.gz` 包含累计工程、Gradle Wrapper、RUN/VERSIONS 与 00–17 来源及实验记录；`.sha256` 检查包是否完整。

```bash
sha256sum -c kotlin-language-17.tar.gz.sha256
mkdir -p /tmp/kotlin-17-replay
tar -xzf kotlin-language-17.tar.gz -C /tmp/kotlin-17-replay
cd /tmp/kotlin-17-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线运行要求本机 JDK 21 和已缓存依赖；从仓库运行 `bash examples/kotlin-language/verification/17.sh` 可复核隔离的 `@DslMarker` 编译拒绝。`verification/17-implicit-parent.kt` 是预期失败样本，不进入正常编译源码集。DSL 目前只生成内存值，旧 CLI 和持久化层均未接入。
