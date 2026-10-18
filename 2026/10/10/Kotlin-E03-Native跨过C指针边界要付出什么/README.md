# Kotlin E03 复跑材料

`kotlin-language-E03.tar.gz` 包含主线 JVM 工程、E02 多平台状态模型与 E03 的 linuxX64/C 互操作源文件。Android E01 实验工程和所有构建产物不在包内；C 静态库由 `verify-native.sh` 在解包后本地生成。

```bash
sha256sum -c kotlin-language-E03.tar.gz.sha256
tar -xzf kotlin-language-E03.tar.gz
cd kotlin-language
bash shared-model/verify-native.sh
./gradlew --offline --no-daemon --console=plain clean test loopbackTest packageTest
PATH=/path/to/node-22/bin:$PATH npm_config_offline=true ./gradlew -p shared-model --offline --no-daemon --console=plain jvmTest jsNodeTest
```

环境需有已校验/缓存的 Gradle、Kotlin/Native 2.2.21 及其平台依赖、Linux x86_64、GCC、JDK 21、Node 22/npm；初次缺缓存应先核对官方来源再获取。`writing-plans/kotlin/verification/E03/` 留初次失败、修正后的原始测试输出及实际页面，Apple/Swift 目标未复跑。
