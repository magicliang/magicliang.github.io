# Scala 39 重跑

仓库根目录执行；`JAVA_HOME` 必须指向 JDK 21，Python 3 使用标准库。工具会下载到临时缓存，并核验 Maven Central 的摘要。

```bash
export SCALA_LAB_JAVA_HOME="$JAVA_HOME"
python3 examples/scala-lab/modules/39/run.py --run-id local-ch39
python3 examples/scala-lab/run.py chapter 39 --run-id local-ch39-unified
```

冻结：Scala 3.3.7、Scala CLI 1.9.1；迁移回归另使用 Scala 2.13.16。已实测 JDK 为 Amazon Corretto 21.0.11。独立模块先输出 Scala class，再显式编译 Java 回执类，最终直接运行 JVM 程序。

源码：`examples/scala-lab/snippets/39/`；合法与故障文件：`examples/scala-lab/modules/39/inputs/`；双版本金额回归：`MigrationRegression.scala`。

已运行证据：`examples/scala-lab/modules/39/evidence/20261002-ch39-complete/`。正例 exit=0；故障行 exit=2；文件缺失 exit=3；错误参数 exit=64。`correctness.log` 保存关闭先于报价、超时后工作继续、资源双失败、Java 格式化、同步/异步报价失败、空批次及行数超限等断言的真实结果；同名 JSON 保存命令与退出码。旧的 `20261002-ch39` 和 `20261002-ch39-final` 保留曾经失败的诊断，不作为成功证据。`20261002-ch39-verified` 为先前已通过的较小断言集合；公共入口的通过记录在 `evidence/20261002-ch39-unified-r2/`，最终统一回归另行记录。

限制：只支持无引号四列文本、CNY、一万行内存批次、批内去重；无真实远程服务、持久化或集群。100 毫秒超时只改变观察结果，不取消原始 Future。双版本回归只覆盖纯金额核心。
