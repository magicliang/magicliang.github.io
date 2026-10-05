36 / 观测合同（NOT_RUN 的扩展，不是观测输出）

入口：examples/javaee-enterprise/README.md；预先部署隔离 javaee_lab 和 Open Liberty WAR。JAVAEE_DEMO_MODE=true 不得对公网开放。
可执行基线：在 examples/javaee-enterprise 下 curl -fsSi --max-time 10 "http://127.0.0.1:${JAVAEE_PORT}/procurement/api/health"；响应头应包含 X-Request-ID，正文为 ready。bash scenarios/09-lab-procurement.sh 检查顺序采购终态。
可执行故障：bash scenarios/18-lab-rollback.sh 断言 HTTP 500 且没有已提交申请行；不验证遥测。
扩展验收：冻结 collector、SDK/agent、broker 版本与运行配置；保存入口/SQL/发布/消费关联 ID 与业务账本，记录采样策略。分别制造上下文断链、导出端不可用；比较业务数据库提交与后端遥测，记录出口错误/缓冲丢弃。当前均 NOT_RUN；不要将 requestId 响应头称为完整追踪。
