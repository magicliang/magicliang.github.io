# Go 38 独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

校验 `sha256sum -c SHA256SUMS`，解压 `tar -xzf go-language-38.tar.gz`。进入解压后的 `go-language`：固定 Go 1.27.1/linux-amd64、`GOTOOLCHAIN=local`、`GOWORK=off`，按 `verification/38.sh` 运行实际二进制（脚本读取 `GO_LANGUAGE_SERVE_DSN`），不要将 SQL 证据替换成纯 `httptest`。

仓库提供的 `writing-plans/go-language/scripts/verify-next.sh 38 '构建配置与诊断端点怎样交付任务服务'` 从新解压目录执行 SHA 核验、单独初始化 PostgreSQL 16、两包 Go 测试、race、构建、CLI 与 `verification/38.sh`；运行环境需要 `psql`、PostgreSQL 16 命令、`curl`、`python3` 与 Go 1.27.1。真实证据见素材目录 `unpack-*` 与包内 `evidence/38/`；先前数据库污染的失败证据保留于 `evidence/38/pilot-shared-db/`。

看到 202 后仍须按响应 ID 查询 SUCCEEDED，并分别核查数据库终态、退出码与端口再次绑定。没有 `GO_LANGUAGE_SERVE_DSN` 时，服务只提供内存任务；不得把这一轮当成数据库验收。网站生成检查只覆盖链接/呈现，不覆盖任务生命周期或其他平台。
