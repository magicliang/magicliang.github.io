# Chapter 38

在完整仓库 `examples/java-libraries` 运行。测试 Java 8 源码，分别使用 JDK 8 和 21。正常依赖固定 Guava 33.5.0-jre；旧 jar 不进入 Maven 正常依赖图，不用于生产。

```sh
mkdir -p /tmp/java-libraries-guava-old
curl -fL https://repo.maven.apache.org/maven2/com/google/guava/guava/30.1.1-jre/guava-30.1.1-jre.jar -o /tmp/java-libraries-guava-old/guava-30.1.1-jre.jar
shasum -a 256 /tmp/java-libraries-guava-old/guava-30.1.1-jre.jar
cd examples/java-libraries
JAVA_HOME=/path/to/jdk8 ./mvnw -B -ntp -s .mvn/settings.xml -DoldGuavaJar=/tmp/java-libraries-guava-old/guava-30.1.1-jre.jar -Dtest=Chapter38Test clean verify
# 保存 target/chapter38-forks 和 target/surefire-reports，再切换 JDK
JAVA_HOME=/path/to/jdk21 ./mvnw -B -ntp -s .mvn/settings.xml -DoldGuavaJar=/tmp/java-libraries-guava-old/guava-30.1.1-jre.jar -Dtest=Chapter38Test clean verify
```

旧 jar SHA-256 必须为 `44ce229ce26d880bf3afc362bbfcec34d7e6903d195bbb1db9f3b6e0d9834f06`；本轮新 jar 为 `1e301f0c52ac248b0b14fdc3d12283c77252d4d6f48521d572e7d8c4c2cc4ac7`。附件不打包旧 jar。

两个测试应通过：新进程退出 0 输出 value=2；旧进程退出 1，stderr 为 NoSuchMethodError 并包含 buildKeepingLast。旧进程预期失败不代表 Maven 应失败。每个进程最长等待 20 秒，测试保存 command、SHA、stdout、stderr、exit；CodeSource 与规范化真实路径比较。

```sh
javap -classpath /tmp/java-libraries-guava-old/guava-30.1.1-jre.jar 'com.google.common.collect.ImmutableMap$Builder'
javap -classpath /path/to/guava-33.5.0-jre.jar 'com.google.common.collect.ImmutableMap$Builder'
javap -c -classpath target/test-classes 'blog.libraries.Chapter38Test$BinaryCompatibilityProbe'
```

前两项分别观察旧版缺失/新版存在 buildKeepingLast；第三项观察 invokevirtual 的真实调用目标。单引号保护 `$`，不要让 shell 展开嵌套类名。

本次独立复本命令额外使用 `-o -Dmaven.repo.local=/tmp/java-libraries-m2`，MAVEN_USER_HOME 指向工程预热的 `.maven-user-home`。公开复现首次运行不加离线参数。实际 JDK 版本见 evidence/38/jdk*-environment.txt，原始 XML 和进程输出见 evidence/38。下载来源为官方 Maven Central；源码按固定 Git SHA 引用。未测试容器类加载、Android、模块路径或替代实现。
