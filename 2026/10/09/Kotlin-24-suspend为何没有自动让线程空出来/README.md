# Kotlin 24 素材与复跑

`suspend-wait-gates.svg` 区分虚拟时钟和真实单线程工作者的观测。`kotlin-language-24.tar.gz` 收录完整累计工程、Gradle Wrapper、RUN/VERSIONS、研究与原始证据；其内容不等于线上网站部署。

```bash
sha256sum -c kotlin-language-24.tar.gz.sha256
mkdir -p /tmp/kotlin-24-replay
tar -xzf kotlin-language-24.tar.gz -C /tmp/kotlin-24-replay
cd /tmp/kotlin-24-replay/kotlin-language
./gradlew --offline --no-daemon --console=plain clean test
./gradlew --offline --no-daemon --console=plain run --args='submit alpha'
```

离线运行需先在本机缓存 Gradle 8.14 和所列精确依赖；无缓存时需要从受信任的仓库下载，不能把“依赖解析失败”误写成测试成功。`verification/24/` 保存具体环境、退出码和正反断言。
