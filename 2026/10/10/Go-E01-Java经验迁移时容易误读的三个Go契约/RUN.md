# Go E01 独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

校验 `sha256sum -c SHA256SUMS`，执行 `tar -xzf go-language-E01.tar.gz` 并进入全新解包的 `go-language`。需要 Go 1.27.1/linux-amd64、PostgreSQL 16、`rg`、`psql`、`python3`。用全新临时目录 `initdb -D "$PGDATA" -A trust -U admin --no-instructions`，以 `pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start` 在 loopback 启动数据库。设置 `GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=postgres sslmode=disable"`、`PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH`、`GOTOOLCHAIN=local`、`GOWORK=off`。

执行 `sha256sum -c evidence/E01/source-sha.stdout`、`go mod verify`、`go test -count=10 -run '^TestElectiveJava' -v .`、`go test -count=1 ./...`、`go test -race -count=1 ./...`、`go build -o taskstats .`。在日志中逐项核对 nil 指针却有非 nil error 接口、快照更改未写回 store、取消 202 时 RUNNING 而释放后 CANCELED，不能只看总 PASS；停止并删除本轮数据库。

仓库外层复跑入口 `writing-plans/go-language/scripts/verify-next.sh E01 'Java经验迁移时容易误读的三个Go契约'` 新建解包目录和专属 PostgreSQL/双缓存，原始输出记录在素材目录 `unpack-*`。页面检查与素材下载是另一项验收，不替代上面的 Go 测试和 SQL 回归。
