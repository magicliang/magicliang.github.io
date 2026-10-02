# E08 复跑

下载 java-libraries-processors.tar.gz，解包后进入同名目录。

```bash
tar -xzf java-libraries-processors.tar.gz
cd java-libraries-processors
./mvnw -B -ntp -s .mvn/settings.xml clean verify
```

首次运行需从 Maven Central 下载固定依赖；本实验已在 Zulu 8.0.472 与 Corretto 21.0.11 分别验证。JAVA_HOME 指向所选 JDK。处理器模块4个测试，生成源在target/generated-sources/annotations；javap命令见包内README。本章 4 tests / 0 failures / 0 errors / 0 skipped。raw stdout/XML 位于仓库 examples/java-libraries/evidence/E08/。

真实annotation processor必须启用；只复制旧class不能代替clean验证。mapstruct API、processor、Lombok provided与binding路径用途不同。
