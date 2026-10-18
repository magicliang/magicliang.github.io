# Kotlin 32 实验复跑

`live-updates.svg` 对照冷流双收集、StateFlow 的最新值、SharedFlow 的 replay=0/1 与作用域退出。归档是完整累计工程与逐篇证据快照，未接入持久化事件日志；在有冻结依赖缓存的机器上复跑：

```bash
sha256sum -c kotlin-language-32.tar.gz.sha256
mkdir -p /tmp/kotlin-32-replay
tar -xzf kotlin-language-32.tar.gz -C /tmp/kotlin-32-replay
cd /tmp/kotlin-32-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

错误输入复核：`./gradlew --offline --no-daemon --console=plain run --args=submit` 应非零退出。32 的归档解包及真实页面输出另见仓库 `writing-plans/kotlin/verification/32/`。
