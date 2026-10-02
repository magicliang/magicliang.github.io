# 第 02 篇实验

仓库根目录进入 `examples/java-libraries` 后执行：

```bash
./mvnw -s .mvn/settings.xml -Dtest=Chapter02Test test
```

完整测试文件：`examples/java-libraries/src/test/java/blog/libraries/Chapter02Test.java`；正文提供相同源码。版本与依赖由第 00 篇及工程 `pom.xml` 冻结。

| 方法 | 二元观测 |
|---|---|
| sourceEditsReachViewButNotCopies | add/set/remove 后视图变化，两个副本成员不变；所有断言通过 |
| allContainersShareMutableElement | 从源或 frozen 取得同一 Item 后改名，各容器读取相同字段值 |
| unsupportedWritesAndMutableCopy | 视图和 Guava 的 add/set/remove 抛 UOE；ArrayList 副本 set 成功且源不变 |
| nullPolicyDiffers | 两种 JDK 构造保留 null；Guava 抛 NPE |
| immutableReuseIsVersionSpecificObservation | 值相等断言通过；身份只打印，不作为业务契约 |
| modernJdkCopyOfIndependentComparison | Java 21 的容器隔离、元素共享、拒写、拒 null 四项断言通过；Java 8 记录 API 不适用 |

Java 8 兼容路径和 Java 21 现代 API 路径分别运行。`NOT_APPLICABLE` 仅表示 Java 8 没有 Java 10+ API，不能算现代场景验收通过。不要将这组顺序测试当作并发可见性、GC 或性能测试。

研究和原始验收材料位于 `examples/java-libraries/evidence/02/`，共享运行环境在 `evidence/00/`。
