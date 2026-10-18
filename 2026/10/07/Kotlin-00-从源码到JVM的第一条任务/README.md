# 00 素材与累计工程

仓库中的活工程：`examples/kotlin-language/`。本目录的 `kotlin-language-00.tar.gz` 为 00 对应的可下载快照，包含源代码、测试、Gradle Wrapper（含 JAR）、`RUN.md`、`VERSIONS.md` 与 `verification/00/` 下的原始实验记录。

下载后执行：

```bash
sha256sum -c kotlin-language-00.tar.gz.sha256
tar -xzf kotlin-language-00.tar.gz
cd kotlin-language
./gradlew --no-daemon clean test
```

真实解包复跑的命令、原始输出与退出码见仓库 `writing-plans/kotlin/verification/00/unpack.txt`。未来章节继续扩展活工程，00 快照不作为后续实现的替代。
