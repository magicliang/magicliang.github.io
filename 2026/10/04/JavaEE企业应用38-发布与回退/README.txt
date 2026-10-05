38 / 发布与回退演练合同（NOT_RUN）

入口：examples/javaee-enterprise/README.md 和 deploy/server.xml。正常现有基线：clean verify，SHA-256 记录实际部署 WAR，依次执行 scenarios/00-health.sh、05-datasource.sh、09-lab-procurement.sh；只可在 127.0.0.1 的隔离库/教学容器操作。
失败门禁：正文使用 psql -v ON_ERROR_STOP=1 -c 'SELECT 1/0' 触发可预期非零退出，检查控制流未执行部署动作；它不是真实迁移或回切验证。
后续要另备新旧应用/配置/schema/真实任务状态版本；在可丢弃旧库副本测试兼容读写、迁移锁与在途事务、回切后订单/申请终态，并保存包 SHA、原始日志和数据库检查结果。当前未提供第二 WAR、升级迁移或滚动脚本；不得标记 PASS。
