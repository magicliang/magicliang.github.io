# 00–02 实验附件

下载同目录 `java-libraries-00-02.tar.gz`，校验同目录 `CHECKSUMS.sha256`，解压并进入 `java-libraries` 后运行：

```bash
./mvnw -B -ntp -s .mvn/settings.xml clean verify
```

需要 JDK 8 或 JDK 21 和首次访问 Maven Central 的网络。Windows 使用 `mvnw.cmd`。

本批已在 Zulu 8u472 与 Corretto 21.0.11 分别执行 29 项测试，全部通过。现代 API 在 Java 8 不适用，Java 21 执行通过。其余 JDK 和平台没有运行。

附件包含完整源码与原始证据；文章中的方法片段不是独立源文件。各章测试可用 `-Dtest=Chapter00Test`、`Chapter01Test`、`Chapter02Test` 单独运行。
