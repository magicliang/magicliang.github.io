01 需求矩阵、研究卡和实验记录模板（2026-10-04）

源码入口（本地现有；GitLab master 链接待推送后核对）：
examples/javaee-enterprise/domain/src/main/java/blog/javaee/domain/{RequestState,ProcurementRequest,LineItem}.java
examples/javaee-enterprise/domain/src/test/java/blog/javaee/domain/ProcurementRulesTest.java
examples/javaee-enterprise/application/src/main/java/blog/javaee/application/{ProcurementUseCases,FixedPriceCatalog}.java
examples/javaee-enterprise/adapters-jdbc/src/main/java/blog/javaee/jdbc/JdbcRequestStore.java
examples/javaee-enterprise/db/migrations/001-initial.sql

状态转换表（输入 → 预期）：
DRAFT → SUBMITTED；SUBMITTED → APPROVED 或 REJECTED；APPROVED → ORDERED。
DRAFT → APPROVED、REJECTED → ORDERED、任一状态自循环、ORDERED → SUBMITTED：拒绝且不写入新状态。
取消与重提：所有来源状态均不支持；没有 CANCELLED 状态或恢复边。

需求与责任：
创建草稿：SKU=paper、数量=2，SKU=pen、数量=3；目录价格 3.50 与 2.25；总额 13.75；非空租户、至少一行、数量>=1、价格>=0、单价无需非零第三位小数。
提交草稿：仅 DRAFT；同租户且需由授权申请人提交（后半句当前未实现）。
审批/拒绝：仅 SUBMITTED；受管身份须为授权审批人（当前未实现）；同版本只能有一次最终决策。
下单：仅 APPROVED，重复 ORDERED 返回原订单；每申请至多一行 purchase_order；同时核对租户、状态、数据库行与事务。
权限矩阵预期：同租户申请人创建与按制度提交自己的草稿；同租户审批人处理已提交申请；订单操作员只对已批准申请下单；跨租户均拒绝。角色/创建人/真实登录目前未实现，不能以 tenantId 参数当身份验证。

领域测试：限定范围内通过。writing-plans/javaee-enterprise/verification/20261004T061900Z-pg16-foundation/build-3.stdout.txt 原始输出记录 ProcurementRulesTest Tests run: 1, Failures: 0, Errors: 0, Skipped: 0；源码中的单个测试方法断言 7.00 金额、合法/非法转换、错误总额与单价精度。不是 13.75 完整采购故事，也没有审批身份结果。server-final.stdout.txt、health.headers.txt、health.body.txt、health-exit-code.txt 只证明 00 的 Open Liberty 健康路由 200 ready。
完整正常路径：隔离教学演示 PARTIAL。writing-plans/javaee-enterprise/verification/20261004T062900Z-pg16-business/ 记录受管容器顺序执行纸品 2 + 笔 3、独立 PostgreSQL 查询 ORDERED|13.75|1、重试返回同一订单。部署时启用 JAVAEE_DEMO_MODE=true，X-Lab-Tenant 可伪造；该运行时源码哈希不能代替现在的完整工作树，不能证明认证、授权或并发。
失败路径：领域单测的非法状态/错误金额与精度拒绝断言通过；writing-plans/javaee-enterprise/verification/20261004T063400Z-pg16-jta-rollback/ 记录插入后的受管事务故障回滚，仅证明申请及明细未提交。重复审批的受控并发最终行、跨租户真实授权、API 金额篡改仍为 NOT_RUN。
复跑顺序：采集代码 SHA、构建 WAR 和实际部署 WAR 的哈希、JDK/Maven/服务器/PostgreSQL 版本和起止时间；在隔离环境运行领域测试，再用真实 PostgreSQL 与受管容器分别核对演示路径和数据库最终行；不可调用 00 健康接口冒充采购结果。
后续归档：完整命令、退出码、领域断言、数据库迁移版本、业务 ID、事务时间线、最后状态/版本/金额/订单行、无敏感信息的拒绝记录。并发使用显式屏障；未有可运行入口的授权路径保持 NOT_RUN，不能以演示租户头替代受管身份。
规范对照：Jakarta EE Platform 11.0、Java SE 21 BigDecimal、PostgreSQL 16 数值与约束；这些资料不规定本例采购流程。
