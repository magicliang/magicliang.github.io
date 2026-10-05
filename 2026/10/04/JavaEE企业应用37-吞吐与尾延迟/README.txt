37 / 容量实验合同，非测试结果

入口：examples/javaee-enterprise/README.md，隔离 PostgreSQL 16 和监听 127.0.0.1 的容器。正常：bash scenarios/00-health.sh、bash scenarios/09-lab-procurement.sh；失败对照：同脚本预审批建单应是 409，bash scenarios/18-lab-rollback.sh 预期 HTTP 500 且数据库无已提交申请行。
当前没有固定请求率发生器、锁等待故障注入器或压测采样记录。准备后分别测固定请求率和固定并发：记录预热、运行时长、发送数、未发起数、超时数、每状态码数、原始时间样本、客户端与服务端资源、schema 与 DB 行终态。改变连接池与数据规模时每次只变一项，运行后按租户核查唯一订单与金额。
不要用健康接口的采样代替业务 p99，更不要把已有归档的单次顺序场景称作压测 PASS。
