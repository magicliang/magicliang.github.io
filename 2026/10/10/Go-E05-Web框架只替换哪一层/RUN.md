# Go E05：框架适配独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

校验 `sha256sum -c SHA256SUMS` 后在新目录解开 `go-language-E05.tar.gz`。设置 Go 1.27.1/linux-amd64 的 `PATH`、`GOTOOLCHAIN=local`、`GOWORK=off`，运行 `go mod download`、`go mod verify`、`sha256sum -c evidence/E05/source-sha.stdout`、`go list -m github.com/go-chi/chi/v5`（须为 `v5.3.2`）。独立数据库仅使用 loopback trust：`initdb -D "$PGDATA" -A trust -U admin --no-instructions`、`pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start`。设置 `GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=postgres sslmode=disable"`。

运行 `go test -count=10 -v -run '^(TestChiAdapter.*|TestHTTPMethodsValidationAndOverload|TestHTTPExplicitCancelWaitsForAnalysisExit)$' .`；确认 chi 两个带后缀用例真实 PASS、SQL 用例无 SKIP。再运行 `go test -count=1 ./...`、`go test -race -count=1 ./...`、`go build -o taskstats .`。新建隔离库 `psql -h 127.0.0.1 -p "$PGPORT" -U admin -d postgres -c 'CREATE DATABASE goe05live'`，设置 `GO_LANGUAGE_SERVE_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=goe05live sslmode=disable"`，运行 `bash verification/E05.sh "$(pwd)/taskstats" "$(mktemp -d)"`，检查真实进程的 HTTP 与 SQL 响应、进程退出码。最后停止本轮 PostgreSQL。

仓库脚本 `writing-plans/go-language/scripts/verify-next.sh E05 'Web框架只替换哪一层'` 新建 SQL 与 Go 双缓存，保存 `unpack-*`；页面/下载须单独核对，不替代 HTTP/SQL 实验。chi 中间件头不提供身份认证。
