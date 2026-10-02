# E05 复跑

下载 java-libraries-extensions.tar.gz，解包后进入同名目录。

```bash
tar -xzf java-libraries-extensions.tar.gz
cd java-libraries-extensions
./mvnw -B -ntp -s .mvn/settings.xml clean verify
```

首次运行需从 Maven Central 下载固定依赖；本实验已在 Zulu 8.0.472 与 Corretto 21.0.11 分别验证。JAVA_HOME 指向所选 JDK。扩展包含E03/E04/E05共10个测试；单章可增加 -Dtest=Extension05Test。本章 3 tests / 0 failures / 0 errors / 0 skipped。raw stdout/XML 位于仓库 examples/java-libraries/evidence/E05/。

所有命令行都是直接String[]，不执行shell。配置与敏感属性使用合成值，反射前白名单拒绝。没有读取外部真实环境或热更新配置。
