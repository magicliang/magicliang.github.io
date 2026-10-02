# E01 复现实验

版本：Guava 33.5.0-jre。源码SHA：8868c096cfdabbe38170b6e395369c315cfb72a1。

Java8源码基线，Zulu8u472与Corretto21.0.11均已实测。

从博客仓库根目录运行：

```sh
cd examples/java-libraries
./mvnw -B -ntp -Dtest=blog.libraries.Extension01Test test
```

首次运行需下载Maven依赖，切换JAVA_HOME即可选择JDK。测试在src/test/java中的位置按工程区分，现代章位于modern/src/test/java。附件完整测试与主工程文件逐字节相同。

独立正文程序为DependencyGraph.java，LIBRARY_CP应设置为该工程实际运行classpath中的依赖JAR路径（见evidence/E01/jdk8-snippet.stdout.txt的实际命令；不同电脑需替换路径）：

```sh
javac -cp "$LIBRARY_CP" DependencyGraph.java
java -cp ".:$LIBRARY_CP" DependencyGraph
```

Graph/ValueGraph/Network同一端点数据分别2/2/3条边，asGraph为2；四节点含orphan；Graph重复边false、ValueGraph替换返回10、Network重复edge对象端点冲突IAE；有向反向不存在、自环拒绝和无向自环degree2；配置nodes插入顺序；successors实时只读视图、ImmutableGraph快照不变；添加反向形成环；JDK邻接Map保留孤立节点和纯终点。

输入均本地创建，不接外部生产服务。没有巨大文件或耗尽资源操作。

未执行边界：并发图修改、删除节点后视图全部操作、图算法性能/内存未测。

证据：examples/java-libraries/evidence/E01/ 中的raw Maven stdout、JUnit XML、snippet日志、source-inspection.txt和claim-ledger.md。本文不以测试通过代替Hexo页面验收。
