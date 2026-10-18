# 第 36 章累计工程独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

Go 1.27.1 linux/amd64、PostgreSQL 16.15、可用模块镜像；仓库 `writing-plans/go-language/scripts/verify-next.sh 36 trace与阻塞profile怎样拆开等待时间` 会在新工程目录、隔离 PostgreSQL、新模块/编译缓存解包运行，保存命令/双流/退出码。`trust` 只用于 loopback 临时数据库。

```bash
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-36-reader.XXXXXX)
tar -C "$reader" -xzf go-language-36.tar.gz
pgdata=$(mktemp -d /tmp/go-language-36-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-36-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-36-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
GO_LANGUAGE_PROFILE_DIR="$reader" go test -count=1 -run '^TestTaskWaitProfiles$' -v .
go tool pprof -top -nodecount=20 "$reader/block.pprof"
go tool pprof -top -nodecount=20 "$reader/mutex.pprof"
go tool trace -pprof=sync "$reader/trace.out" > "$reader/trace-sync.pprof"
go tool pprof -top -nodecount=20 "$reader/trace-sync.pprof"
go tool trace -pprof=sched "$reader/trace.out" > "$reader/trace-sched.pprof"
go tool pprof -top -nodecount=20 "$reader/trace-sched.pprof"
go tool trace -d=parsed "$reader/trace.out" > "$reader/trace-parsed.txt"
rg 'task\[0\]|task\[1\]' "$reader/trace-parsed.txt"
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

零期限 CLI 预期退出 2，其余命令为 0。`runtime.SetBlockProfileRate(1)` 与 mutex 采样、trace 本身都可能影响时间，不以本轮墙钟作生产 SLA；block/mutex/sched profile 不能充当 CPU profile。本章锁与排队实验走内存及 httptest，真实 SQL 是另一路径的全量回归；没有 DSN 的 SKIP 不是数据库通过。页面不替代 Go/SQL 测试。
