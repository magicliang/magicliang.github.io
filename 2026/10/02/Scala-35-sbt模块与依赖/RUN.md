# 第 35 篇实验说明

LAB_VERIFIED。正文基于最终独立运行 20261002-ch35-r3，固定 sbt 1.11.7 / JDK 21.0.11-amzn / Scala 3.3.7、2.13.16；旧运行只保留故障定位，不作为完成证据。

## 从仓库根目录复现

```bash
export SCALA_LAB_JAVA_HOME=/path/to/jdk21
export SCALA_LAB_CLI_JAR=/path/to/scala-cli-1.9.1.jar
python3 examples/scala-lab/modules/35/run.py --run-id local-35
python3 examples/scala-lab/run.py chapter 35 --run-id local-35-smoke
```

独立实验只需要 JDK 环境变量；第二条共享烟雾实验使用 CLI，未指定 jar 时由共享工具目录提供。runner 核对工具下载校验和，在新的临时目录复制工程，使用本次运行专属 Ivy 本地仓库，不发布到公共仓库。

## 对照源码与日志

正常源码：examples/scala-lab/modules/35/core、cli、consumer。完整 build.sbt 还定义仅携带依赖的 bridge、strict 冲突项目与 aggregateOnly 对照。各模块的 Test / test 明确执行带断言的 Test / runMain，没有第三方测试框架。

原始证据：examples/scala-lab/modules/35/evidence/20261002-ch35-r3/。每个名字都有 .json 保存完整命令/cwd/exit/patterns，以及 .log 保存输出。

| 日志名 | 实际出口 | 对应事实 |
|---|---:|---|
| cross-tests | 0 | 两版本各执行核心与CLI断言，总额500、核心空输入0 |
| publish-consume | 0 | 本地_2.13/_3发布，两个消费者断言500 |
| incremental-noop | 0 | 未修改时没有新增源码编译 |
| incremental-implementation | 0 | 核心实现修改重编译，CLI断言仍500 |
| reverse-dependency | 1 | core不可引用cli |
| test-scope-leak | 1 | cli Test不可见core测试夹具 |
| aggregation-not-classpath | 1 | 单纯aggregate没有核心类路径 |
| publish-conflict-fixtures | 0 | 发布自建core0.1.1和bridge |
| strict-conflict | 1 | 自建组织中0.1.0与0.1.1请求冲突 |
| conflict-override | 0 | 明确覆盖后解析0.1.1 |
| fresh-rebuild | 0 | 新源码目录重建核心、CLI和消费者 |

另有 environment 的 JDK 检查，合计12次外部调用；4个失败均核对目标诊断。published-artifacts.json保存发布jar哈希，实际二进制jar含Order.class且不含CoreTestFixture/CoreCheck。

共享入口：examples/scala-lab/snippets/35/Chapter35.scala，main类scalaexamples.Chapter35。已运行的共享证据examples/scala-lab/evidence/20261002-ch35/35.log/.json，exit0，输出：

```text
35 order arithmetic passed; actual sbt boundaries in modules/35
```

## 边界

strict只针对lab.scala35组织；全局strict还可能拒绝文档工具传递依赖的淘汰。override只验证解析选择，不能证明任意新版本兼容。干净重建不复用target，但复用工具与下载缓存及本轮已发布仓库；没有空缓存、离线或新操作系统验证。正文的discount修改练习未纳入已跑实验。

文章固定源码链接对应sbt v1.11.7解引用提交9d2a5f478bde5d45562423cb6decf92b255b9517。说明汇总位于writing-plans/scala/verification/35-lab.md，文章核验回执在.omo/evidence/scala-07-21/ch35-article-verification.txt。

