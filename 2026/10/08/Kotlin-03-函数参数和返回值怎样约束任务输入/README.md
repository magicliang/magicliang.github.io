# 03 素材与累计工程

`kotlin-language-03.tar.gz` 包含完整 Kotlin/JVM 累计源码、测试、Gradle Wrapper（含 JAR）、RUN/VERSIONS 与 00–03 的原始证据。运行环境须有 JDK 21 与预先缓存的 Gradle 依赖；联网安装时仍应验证 Wrapper 的分发包 SHA。

```bash
sha256sum -c kotlin-language-03.tar.gz.sha256
tar -xzf kotlin-language-03.tar.gz
cd kotlin-language
./gradlew --offline --no-daemon clean test
```

这是一次预览函数参数与返回类型的实验，不会创建、提交或执行任务。真实解包复跑的命令和结果见仓库 `writing-plans/kotlin/verification/03/unpack.txt`；不能以文本中的期望命令替代解包验收。
