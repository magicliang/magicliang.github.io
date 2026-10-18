# E07 独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先在本目录执行 `sha256sum -c SHA256SUMS`，到新目录执行 `tar -xzf go-language-E07.tar.gz -C "$NEW_DIRECTORY"` 并进入 `$NEW_DIRECTORY/go-language`。使用 Go 1.27.1/linux-amd64，设置 `GOTOOLCHAIN=local`、`GOWORK=off`，在新缓存 `GOMODCACHE`/`GOCACHE` 中执行 `go mod download`、`go mod verify` 和 `sha256sum -c evidence/E07/source-sha.stdout`。准备独立的 PostgreSQL 16 trust loopback 实例，设置 `GO_LANGUAGE_SQL_DSN` 指向其 `postgres` 库。

先执行 `GOWORK=auto bash verification/E07.sh "$OUTPUT_DIRECTORY"`。它会分别保存 `go.work` 诊断、独立 consumer 的缺失依赖非零退出、本地替换后的无 workspace 构建、不兼容 API 编译错误、原服务实际 ID 的终态及 SQL 核账、子进程信号退出；不可用工作区内构建代替失败反例。再以 `GOWORK=off` 执行 `go test -count=1 -v ./...`、`go test -race -count=1 ./...` 以及原 CLI 正反用例。`require v0.1.0` 是本地演示版本声明，没有发布，远程获取为 `NOT_RUN`；必须保留 `client/` 本地副本与显式替换，才算这里验证过的独立构建条件。
