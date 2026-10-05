39 / 可执行部分与最终放行清单（不是 PASS 报告）

入口：examples/javaee-enterprise/README.md，单机隔离 javaee_lab / Open Liberty，JAVAEE_DEMO_MODE=true 仅在 127.0.0.1。
现成正常路径：bash scenarios/00-health.sh && bash scenarios/05-datasource.sh && bash scenarios/09-lab-procurement.sh；后者应输出最终 ORDERED|13.75|1。
现成失败路径：bash scenarios/18-lab-rollback.sh，应报告注入 HTTP 500 且提交行数 0。再运行 09-lab-procurement.sh 检查新租户的业务仍可用；两个脚本的运行顺序不是并发审批证据。
放行前另需：认证主体与每个对象/租户权限；两个连接并发审批/建单的最终行集合；DB 断连与提交结果未知；broker 发送、消费、重投、去重与终态；旧库迁移、双版本应用回切及在途任务恢复；压测原始数据、日志与 trace 断链实验。当前工程未提供这些运行入口和证据，状态 NOT_RUN。
保存每一项输入、实际 HTTP/消息输出、数据库终态、运行版本、WAR SHA、配置摘要与原始命令/退出码；不要在记录里泄露口令。
