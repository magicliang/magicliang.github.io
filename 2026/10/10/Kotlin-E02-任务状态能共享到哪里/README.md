# Kotlin E02 复跑材料

`kotlin-language-E02.tar.gz` 包含原有 JVM 累计工程与 `shared-model` 独立 Kotlin Multiplatform 工程，不含 E01 Android 项目、生成目录与 Gradle 缓存。与正文一致，它保留主线旧测试和两目标公共状态规则。

先以 `sha256sum -c kotlin-language-E02.tar.gz.sha256` 核对字节，再解包并进入 `kotlin-language/`。JDK 21、Gradle 8.14 Wrapper、Node 22.23.2 与已缓存依赖条件下运行：

```bash
./gradlew --offline --no-daemon --console=plain clean test loopbackTest packageTest
PATH=/path/to/node-22/bin:$PATH ./gradlew -p shared-model --offline --no-daemon --console=plain jvmTest jsNodeTest
```

安装包以外的真实 Android/Native/浏览器和外网行为没有包含在本归档的测试结论中。原始 JVM/JS XML、首次 Yarn 解析失败与主线回归见 `writing-plans/kotlin/verification/E02/`。
