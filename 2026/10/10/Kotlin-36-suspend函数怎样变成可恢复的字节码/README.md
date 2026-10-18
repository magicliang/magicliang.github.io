# Kotlin 36 素材与复跑

`suspend-state-machine.svg` 仅画出固定 Kotlin 2.2.21 生成物中的 continuation 与一次挂起/恢复路径。完整累计代码在 `examples/kotlin-language/`；官方规范、源码 blob、`javap` 和累计测试记录见 `writing-plans/kotlin/research/36.md` 与 `writing-plans/kotlin/verification/36/`。

```bash
sha256sum -c kotlin-language-36.tar.gz.sha256
mkdir -p /tmp/kotlin-36-replay
tar -xzf kotlin-language-36.tar.gz -C /tmp/kotlin-36-replay
cd /tmp/kotlin-36-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test loopbackTest
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

非法输入 `./gradlew --offline --no-daemon --console=plain run --args=submit` 预期退出非零。PostgreSQL 16 二进制和 Gradle 缓存须具备，数据库单测会创建独立临时集群，不使用共享实例；真实外部网络故障仍 NOT_RUN。
