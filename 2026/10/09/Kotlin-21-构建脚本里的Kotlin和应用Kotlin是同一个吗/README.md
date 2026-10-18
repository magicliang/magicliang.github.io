# Kotlin 21 素材与复跑

`gradle-domain-boundary.svg` 画出应用项目依赖、领域类与两个模块的测试入口。`kotlin-language-21.tar.gz` 是包含 00–21 累计工程、Gradle Wrapper、RUN/VERSIONS 和必要原始记录的快照；`.sha256` 对打包字节校验，不是验证结果的替身。

```bash
sha256sum -c kotlin-language-21.tar.gz.sha256
mkdir -p /tmp/kotlin-21-replay
tar -xzf kotlin-language-21.tar.gz -C /tmp/kotlin-21-replay
cd /tmp/kotlin-21-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线模式需要本机 JDK 21 和已缓存依赖。在完整仓库执行 `bash examples/kotlin-language/verification/21.sh` 另外生成独立 `javac` 缺失/补齐领域 classpath 的正反例以及依赖图；不要把 `verification/21-domain-classpath.java` 放进默认 Java 源码集。无真实网络、持久化或后台任务。
