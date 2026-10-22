# 后端系统工程 34：素材

- `backend-systems-34.tar.gz`：本篇工程与证据快照（SHA-256 `8575b649c7463ad4fb68594d8a9d318fda377accf946f414ff10df9dabed9ba1`）。内容取自仓库 `batch-3/`：`examples/common`、`examples/shortlink`、`evidence/34`、`CONVENTIONS.md`、`SOURCES.md`。
- 运行：解包后执行 `cd backend-systems-34/examples/shortlink && ./run.sh`。需要 OpenJDK 21、PostgreSQL 16 服务端二进制（默认 `/usr/lib/postgresql/16/bin`，可用 `PGBIN` 覆盖）与 pgJDBC 42.7.7（默认取本地 Maven 仓库，可用 `JDBC_JAR` 指定）。
- 运行会覆盖包内 `evidence/34/output.txt`；正文摘录对应包内原有的那次运行。部分计数随线程调度变化，结论以断言为准。
- 本地实验不证明生产能力，边界见 `evidence/34/LIMITS.md`。该文件只是素材说明，不代表站点已部署。
