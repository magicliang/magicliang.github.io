# 01 素材与累计工程

仓库活工程：`examples/kotlin-language/`。`kotlin-language-01.tar.gz` 冻结 01 时刻的完整源码、测试、Gradle Wrapper、`RUN.md`、`VERSIONS.md` 与 00–01 原始实验记录。00 的压缩包保留当时快照，不能代表 01 的新增代码。

```bash
sha256sum -c kotlin-language-01.tar.gz.sha256
tar -xzf kotlin-language-01.tar.gz
cd kotlin-language
./gradlew --no-daemon clean test
```

Gradle 分发包即使来自镜像，也要按 Wrapper properties 固定的官方 SHA 校验。实际解包复跑与退出码见仓库 `writing-plans/kotlin/verification/01/unpack.txt`；01 的 `verification/01-val-reassignment.kt` 属于预期不能编译的隔离样本，不在默认源码目录里。
