# Scala 37 实验说明

状态：LAB_VERIFIED。冻结 Scala 2.13.16 / 3.3.7，Scala CLI 1.9.1，Corretto 21.0.11。正文仅描述这些版本的实测；Scala 3.8+、宏/插件和隐式迁移边界属于官方文档核验，没有在本实验运行。

## 复现

从仓库根目录执行，替换 JDK 路径，并使用尚未存在的 run-id：

```bash
SCALA_LAB_JAVA_HOME=/path/to/jdk-21 \
python3 examples/scala-lab/modules/37/run.py --run-id replay-37
```

runner 会拒绝复用已有 evidence/target 目录。可通过 SCALA_LAB_CLI_JAR 指定缓存工具；首次准备及摘要校验可能需要访问 Maven。完整子命令与 classpath 由 runner 记录，不需要手工拼接。

## 源码与证据

- 共享金额库：examples/scala-lab/snippets/37/PricingCore.scala。
- 客户端与 runner：examples/scala-lab/modules/37/{LegacyClient.scala,ModernClient.scala,run.py}。
- 实测归档：examples/scala-lab/modules/37/evidence/20261002-ch37/。
- 源码、工具与产物：source-sha256.json、toolchain.json、products-sha256.json；改写保存 rewrite-before.scala.txt 和 rewrite-after.scala.txt。

19 条命令中 17 条退出 0，两条预期退出 1，同时匹配目标诊断。每条命令有同名 JSON 和原始 log。

| 场景 | 日志前缀 | 实际可观察结果 |
|---|---|---|
| Scala 2 同源旧调用 | scala2-legacy-compile / scala2-legacy-run | 编译成功，输出 PASS legacy: 25.20 |
| Scala 3 默认同源拒绝 | scala3-default-reject | 非零；amount 必须带括号的 E100 |
| 自动改写副本 | rewrite | amount 改为 amount()；原件不变 |
| 改写后双版本 | rewritten-compile-* / rewritten-run-* / rewritten-legacy-run-* | 两个版本均编译并运行两个客户端 |
| Scala 2 库 → Scala 3 客户端 | scala2-library-scala3-client / scala2-library-scala3-client-run | 两个客户端编译，实际执行 ModernClient |
| Scala 3 库 → Scala 2 无 reader | scala3-library-scala2-no-reader | 非零；缺少 -Ytasty-reader 目标诊断 |
| Scala 3 库 → Scala 2 有 reader | scala3-library-scala2-reader / scala3-library-scala2-client-run | 编译运行成功 |
| 实际产物检查 | javap-scala2 / javap-scala3 | amount(): scala.math.BigDecimal |

ModernClient 实際断言金额 25.20、0.10、0.32，并用 Try.isFailure 检查零数量拒绝，输出：

```text
PASS migrated: 25.20, 0.10, 0.32; invalid quantity refused
```

Scala 2 库供 Scala 3 消费时，旧客户端可省略括号来自 Scala 2 定义方法豁免；该消费步骤只运行现代客户端，不应把编译成功说成旧客户端也执行。两个 javap 描述符相同也不证明任意 API 的源码或二进制兼容。

## 覆盖边界

没有运行 Scala 3.8/3.9、第三方宏/编译器插件、跨版本隐式候选、远程发布消费或历史客户端二进制直接替换。共享库只公开普通 case class/集合/金额 API，不能据此推论 Scala 2 reader 支持 union、match type、上下文函数或 Scala 3 宏。

