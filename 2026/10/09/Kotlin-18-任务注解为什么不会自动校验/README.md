# Kotlin 18 素材与复跑

`annotation-retention-path.svg` 对照类目标、两种保留期、指定 Class 的 JDK 反射读取与显式校验。`kotlin-language-18.tar.gz` 包含累计完整工程、Wrapper、RUN/VERSIONS、00–18 的来源和原始实验记录；`.sha256` 核对下载包。

```bash
sha256sum -c kotlin-language-18.tar.gz.sha256
mkdir -p /tmp/kotlin-18-replay
tar -xzf kotlin-language-18.tar.gz -C /tmp/kotlin-18-replay
cd /tmp/kotlin-18-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线复跑要求 JDK 21 和已缓存依赖。在完整仓库中运行 `bash examples/kotlin-language/verification/18.sh` 可检查注解目标的隔离编译拒绝与 `javap -v`；`verification/18-invalid-annotation-target.kt` 是预期失败样本，不能复制入常规源码。只用 JDK 反射读取给定类，未添加 `kotlin-reflect` 或扫描容器。
