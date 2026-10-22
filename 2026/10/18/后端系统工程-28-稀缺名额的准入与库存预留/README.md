# 后端系统工程 28：素材

- `backend-systems-28.tar.gz`：本篇工程与证据快照（SHA-256 `a8a86f236f1db759267f13ae748b3eb6b40780c9692457e9b2990e367d08eac7`）。内容取自仓库 `batch-3/`：`examples/common`、`examples/flash-sale`、`evidence/28`、`CONVENTIONS.md`、`SOURCES.md`。
- 运行：解包后执行 `cd backend-systems-28/examples/flash-sale && ./run-28.sh`。需要 OpenJDK 21、PostgreSQL 16 服务端二进制（默认 `/usr/lib/postgresql/16/bin`，可用 `PGBIN` 覆盖）与 pgJDBC 42.7.7（默认取本地 Maven 仓库，可用 `JDBC_JAR` 指定）。
- 运行会覆盖包内 `evidence/28/output.txt`；正文摘录对应包内原有的那次运行。部分计数随线程调度变化，结论以断言为准。
- 本地实验不证明生产能力，边界见 `evidence/28/LIMITS.md`。该文件只是素材说明，不代表站点已部署。
