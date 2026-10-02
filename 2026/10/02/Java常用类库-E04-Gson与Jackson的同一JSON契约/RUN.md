# E04 复跑

下载 java-libraries-extensions.tar.gz，解包后进入同名目录。

```bash
tar -xzf java-libraries-extensions.tar.gz
cd java-libraries-extensions
./mvnw -B -ntp -s .mvn/settings.xml clean verify
```

首次运行需从 Maven Central 下载固定依赖；本实验已在 Zulu 8.0.472 与 Corretto 21.0.11 分别验证。JAVA_HOME 指向所选 JDK。扩展包含E03/E04/E05共10个测试；单章可增加 -Dtest=Extension04Test。本章 4 tests / 0 failures / 0 errors / 0 skipped。raw stdout/XML 位于仓库 examples/java-libraries/evidence/E04/。

Gson重复键检查器只验证根对象；日期默认表示与ISO适配已分开。没有JSON性能基准，未覆盖更长循环图。
