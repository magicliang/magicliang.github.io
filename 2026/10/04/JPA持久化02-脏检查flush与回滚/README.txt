# 02 研究卡：同步与回滚

- 规范：Jakarta Persistence 3.2 §3.3.4、§3.4.2–3.4.3、§3.11.2、§7.5.2–7.5.3；数据库可见性另参 PostgreSQL 16 `READ COMMITTED`。
- 源码入口：[ProcurementJpaTest.java](https://gitlab.alibaba-inc.com/liangchuan.lc/my-blogs/-/blob/master/examples/jpa/src/test/java/blog/jpa/ProcurementJpaTest.java) 的 `rollbackAfterFlushDoesNotPersistTransition()`；`jpa_lab` 独立库。
- 已归档：`writing-plans/jpa/verification/20261004T053805Z-pg16-resource-local/RUN.md`，实际 `clean test` 6/6、退出码 0；方法断言种子提交后修改、flush、rollback、关闭上下文、另开上下文读取 DRAFT。具体 SQL 形状及时间未归档。
- NOT_RUN：正文完整 `AutoFlush02ProbeTest` 未加入工程；JPQL AUTO 查询结果、方法筛选命令、flush 至 rollback 之间的第二连接读取与模拟数据库约束错误均未实测。不得将回滚测试通过扩展为它们也通过。
- 限制：RESOURCE_LOCAL 不能证明 JTA、外部消息原子性或跨 Provider 的 SQL 顺序；异常发生于 commit 时的未知结果另需幂等核对。
