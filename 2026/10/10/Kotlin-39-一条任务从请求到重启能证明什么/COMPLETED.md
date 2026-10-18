# 当前累计工程与章节快照

`kotlin-language-39.tar.gz`、`kotlin-task-service-39.zip` 是 39 首轮章节快照；没有把本轮修改混入旧包。当前交付为 `kotlin-language-completed.tar.gz`、`kotlin-task-service-completed.zip`，校验见 `completed.sha256`。

源码包包含根 JVM/domain、公共多平台模型、选修独立工程与验证入口。先使用 JDK 21，确保 `java` 与 `javac` 都来自它的 bin；设置 `KOTLIN_PG_BIN` 为 PostgreSQL 工具目录，再运行 `bash verification/local.sh`。离线参数要求已有依赖缓存；冷环境需先获取固定版本依赖，不能把缺缓存当代码失败。

普通累计测试、真实回环/发行包、JDBC 与停机路径分别记录；Spring、虚拟线程、ABI、JS/Wasm 使用 `RUN.md` 中独立入口。Android 设备、linuxX64 Native/C、浏览器/WASI 与真实插件没有被 JVM 测试替代。

服务发行包有两个入口：`bin/kotlin-task-language` 只做 CLI 校验，`bin/task-server <port>` 是回环 HTTP 服务。HTTP/JDBC 模式需要显式 `TASK_DB_URL` 及已初始化的 `task_snapshot` 表。测试自行初始化临时集群；普通服务启动不会创建数据库或表。未设置 URL 时只保存进程内状态，重启后没有持久任务保证。
