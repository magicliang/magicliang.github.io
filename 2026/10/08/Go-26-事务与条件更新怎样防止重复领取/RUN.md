# 26 完整工程包：独立复跑 SQL 事务

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-26.tar.gz` 包含单一累计工程、固定版本资料、00–26 研究卡与原始文本证据，不嵌套旧章压缩包。以下过程在**新工程目录、新 PostgreSQL 16 数据目录和新模块缓存**中运行；需本机已有 Go 1.27.1、PostgreSQL 16 和 Python 3：

```sh
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-26-reader.XXXXXX)
tar -C "$reader" -xzf go-language-26.tar.gz
pgdata=$(mktemp -d /tmp/go-language-26-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
psql -h 127.0.0.1 -p "$port" -U admin -d postgres -Atc 'select version()'
cd "$reader/go-language"
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-26-modcache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
go test -count=1 -v ./...
go test -count=30 -run 'TestSQLConcurrentClaimAndTransactionRollback|TestSQLHTTPRunningCancelWaitsForAnalysisExit|TestSQLHTTPQueuedCancelDoesNotStartAnalysis|TestSQLShutdownWaitsForWorkerBeforeTerminal' -v .
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

CLI 零期限预期退出 2，其余命令预期退出 0。`unpack-*` 保存本次实际独立解包与数据库生命周期的命令、stdout、stderr、退出码。`trust` 只用于隔离目录和 127.0.0.1，不适合共享数据库；SQL `Commit` 应答丢失、进程异常退出与外部副作用去重仍 `NOT_RUN`。页面与静态 HTTP 校验不能替代实际 SQL 实验。
