# Kotlin 31 素材与复跑

`flow-collection-boundaries.svg` 对照冷流的两次收集、缓冲上下游、flowOn 的真实线程与 catch 的异常方向。`kotlin-language-31.tar.gz` 包含累计工程、Wrapper、RUN/VERSIONS、来源和原始验证输出；没有上传或部署。

```bash
sha256sum -c kotlin-language-31.tar.gz.sha256
mkdir -p /tmp/kotlin-31-replay
tar -xzf kotlin-language-31.tar.gz -C /tmp/kotlin-31-replay
cd /tmp/kotlin-31-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线命令需已缓存冻结的精确版本依赖。`verification/31/` 有具体环境、两类调度器的实验输出与退出码；示例 Flow 没有真实网络、数据库或持久任务提交。
