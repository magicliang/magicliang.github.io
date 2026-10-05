35 / 隔离测试合同（本文件是步骤，不是运行日志）

起点：仓库根目录 examples/javaee-enterprise/README.md。先准备独立 javaee_lab 库，执行 db/migrations/001-initial.sql；构建 WAR，按 README 部署本机容器，启用仅监听 127.0.0.1 的 JAVAEE_DEMO_MODE=true。不要拿正式环境验证教学接口。
正常：在 examples/javaee-enterprise 中依次执行 bash scenarios/00-health.sh、bash scenarios/05-datasource.sh、bash scenarios/09-lab-procurement.sh；最后一个脚本应输出 ORDERED|13.75|1，且退出码为 0。
故障：bash scenarios/18-lab-rollback.sh 应输出 HTTP 500、committed_requests_after_failure=0，脚本退出码为 0。原始状态码 500 是预期注入，不等于脚本失败。
另存：命令、退出码、数据库版本、构建物/已部署 WAR 与源码摘要、服务器配置、stdout/stderr、数据库终态；不要把过去的归档误作本次实验。
待补：旧库增量迁移、双连接竞争、身份授权及消息故障均 NOT_RUN。
