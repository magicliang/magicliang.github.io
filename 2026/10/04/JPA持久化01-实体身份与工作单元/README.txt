# 01 研究卡：身份与脱管

- 规范：Jakarta Persistence 3.2 §3.1、§3.3.2、§3.3.6–3.3.8、§3.4、§7.7–7.8。
- 源码：[ProcurementJpaTest.java](https://gitlab.alibaba-inc.com/liangchuan.lc/my-blogs/-/blob/master/examples/jpa/src/test/java/blog/jpa/ProcurementJpaTest.java)、[ProcurementRequest.java](https://gitlab.alibaba-inc.com/liangchuan.lc/my-blogs/-/blob/master/examples/jpa/src/main/java/blog/jpa/ProcurementRequest.java)。使用真实 `examples/jpa/` 和独立 `jpa_lab` 库，不另建教学单元。
- 已归档输入与结果：`writing-plans/jpa/verification/20261004T053805Z-pg16-resource-local/RUN.md` 的 Java 21.0.12.1、PostgreSQL 16.15、Hibernate 7.1.36.Final、整套 `clean test` 6/6、退出码 0；`lifecycleAndServerCalculatedTotal` 断言同上下文引用相同、提交后 clear 再 find 引用不同、回读金额/明细。
- NOT_RUN：正文中的 `Detached01ProbeTest` 仅为完整待加入测试代码；未保存为工程文件、未执行单方法筛选命令；不能把已有 6/6 当成脱管修改未写入的原始观测。
- 限制：`contains` 是当前上下文成员资格，不是数据库存在性或租户授权。未观测脱管修改时的 SQL；已有 Hibernate 专题证据不参与本章验收。
