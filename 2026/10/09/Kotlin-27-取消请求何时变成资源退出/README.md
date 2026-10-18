# Kotlin 27 素材与复跑

`cancellation-resource-ownership.svg` 将协作检查、资源交接、虚拟超时与真实外部操作分成不同的验收边界。`kotlin-language-27.tar.gz` 是累计工程、Wrapper、RUN/VERSIONS、研究与原始证据快照；没有发布或上传。

```bash
sha256sum -c kotlin-language-27.tar.gz.sha256
mkdir -p /tmp/kotlin-27-replay
tar -xzf kotlin-language-27.tar.gz -C /tmp/kotlin-27-replay
cd /tmp/kotlin-27-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线命令要求本机已缓存精确版本的依赖。真实线程循环与虚拟超时测试分别见 `verification/27/CancellableTaskRunTest.txt`；没有外部驱动取消成功或事务提交的证据，不能混用。
