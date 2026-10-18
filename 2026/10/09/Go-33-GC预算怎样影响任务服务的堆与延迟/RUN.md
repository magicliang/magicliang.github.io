# 第 33 章累计工程独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

环境：Go 1.27.1 linux/amd64、PostgreSQL 16.15、模块镜像可达。仓库 `writing-plans/go-language/scripts/verify-next.sh 33 GC预算怎样影响任务服务的堆与延迟` 在新目录、新隔离库、新模块/编译缓存实际复跑并保存 `.command/.stdout/.stderr/.exit`。`trust` 只适用于 loopback 临时数据库。

```bash
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-33-reader.XXXXXX)
tar -C "$reader" -xzf go-language-33.tar.gz
pgdata=$(mktemp -d /tmp/go-language-33-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-33-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-33-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
GOGC=50 GOMEMLIMIT=64MiB go test -count=5 -run '^TestTaskGCBudget$' -v .
GOGC=200 GOMEMLIMIT=64MiB go test -count=5 -run '^TestTaskGCBudget$' -v .
GOGC=200 GOMEMLIMIT=64MiB go test -count=5 -run '^TestTaskGCBudget$' -v .
GOGC=50 GOMEMLIMIT=64MiB go test -count=5 -run '^TestTaskGCBudget$' -v .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

零期限的 CLI 命令预期退出 2，其他命令应为 0。GC 实验只测 `httptest` handler 与内存任务存储，真实 SQL 测试是累计工程的独立回归；缺少真实 DSN 的 SKIP 不算真库验收。`GOMEMLIMIT=64MiB` 在本例没有触顶，不可拿结果说明低内存条件下如何退化。静态页面检查不替代 Go/SQL 实验。
