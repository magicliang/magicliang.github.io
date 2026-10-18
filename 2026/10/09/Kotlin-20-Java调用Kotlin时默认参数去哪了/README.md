# Kotlin 20 素材与复跑

`java-consumer-api.svg` 对照 `@JvmStatic`、`@JvmOverloads` 与 `@Throws` 面向 Java 源码的独立作用。`kotlin-language-20.tar.gz` 含 00–20 完整累计工程、Gradle Wrapper、RUN/VERSIONS 与原始实验记录；`.sha256` 校验归档字节。

```bash
sha256sum -c kotlin-language-20.tar.gz.sha256
mkdir -p /tmp/kotlin-20-replay
tar -xzf kotlin-language-20.tar.gz -C /tmp/kotlin-20-replay
cd /tmp/kotlin-20-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线运行需要本机 JDK 21 和已缓存依赖。仓库内运行 `bash examples/kotlin-language/verification/20.sh` 额外用单独 `javac` 保存默认参数的预期编译拒绝，并运行 `src/test/java` 的真实 Java 消费者。`verification/20-invalid-java-overload.java` 不能放进常规 Java 源码集。`readTask` 抛的是合成 IOException，没有实际存储 IO 或库发布。
