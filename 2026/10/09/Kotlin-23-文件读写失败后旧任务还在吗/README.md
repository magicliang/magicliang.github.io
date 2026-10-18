# Kotlin 23 素材与复跑

`file-resource-paths.svg` 标出 Reader 的 EOF / 提前返回 / 失败关闭、暂存文件移动与子进程退出的不同完成点。`kotlin-language-23.tar.gz` 含 00–23 累计双模块工程、Gradle Wrapper、RUN/VERSIONS 和必要原始输出；`.sha256` 校验归档字节。本篇文件写入故障是合成注入，固定进程探针只调用本机 JDK，不接受任意输入。

```bash
sha256sum -c kotlin-language-23.tar.gz.sha256
mkdir -p /tmp/kotlin-23-replay
tar -xzf kotlin-language-23.tar.gz -C /tmp/kotlin-23-replay
cd /tmp/kotlin-23-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
./gradlew --offline --no-daemon --console=plain run --args=submit # 预期非零
```

离线模式需要本机 JDK 21 和已缓存依赖。完整仓库中可运行 `bash examples/kotlin-language/verification/23.sh` 留存两类测试的 JUnit XML、CLI 正反和原始退出码；本篇没有真实网络/数据库/后台任务，临时文件 `/tmp` 的一次原子移动不代表跨 provider 或断电持久性。
