# 07 研究卡：事务、版本与行锁

- 规范：Persistence 3.2 §3.3.4、§3.4.3、§3.5.1–3.5.5、§7.5；PostgreSQL 16 的 Transaction Isolation、Explicit Locking 与 `lock_timeout` 文档。
- 工程入口：`examples/jpa/src/test/java/blog/jpa/ProcurementJpaTest.java` 中 `rollbackAfterFlushDoesNotPersistTransition`、`optimisticConflictWithControlledInterleaving`；本地事务使用 `examples/jpa/src/main/resources/META-INF/persistence.xml`。文章中的 Maven 命令需要专用 `jpa_lab` 库与工程 README 的环境变量。
- 正常/失败断言：回滚后 DRAFT；A 先审批成功，B 基于旧版本拒绝时失败，独立上下文读取 APPROVED。记录完整异常链，不能把宽泛的 `RuntimeException` 断言说成精确类型检验。
- 悲观锁待实验：专用测试行；psql 会话 A `BEGIN; SELECT id FROM purchase_request WHERE id = <测试ID> FOR UPDATE;` 并停住；会话 B `BEGIN; SET LOCAL lock_timeout = '1s'; SELECT id FROM purchase_request WHERE id = <测试ID> FOR UPDATE;`，记录等待/失败；B 若报错则 `ROLLBACK`，A `COMMIT`，另起事务核对行。确保两个独立连接及同一已提交测试行，测试后不得遗留未提交事务。JPA `PESSIMISTIC_WRITE` 仍须另加双 EntityManager 栅栏测试，不能把 SQL 测试冒充 JPA 通过。
- JTA 待实验：真实容器、JTA unit、受管数据源和事务边界；独立记录提交/回滚、异常与数据库终态。当前没有容器入口，不用本地事务结果替代。
- 证据与状态：`writing-plans/jpa/verification/20261004T053805Z-pg16-resource-local/RUN.md` 的 `clean test` 6/6 PASS，含上述两项本地事务断言；代码逐文件 SHA、原始测试输出与退出码在同目录。迁移命令退出 0，但迁移 stdout 未归档，不算独立迁移验收。筛选命令、悲观锁两连接和真实 JTA 均未单独执行，NOT_RUN；不得用本地回归推出 JTA PASS。
