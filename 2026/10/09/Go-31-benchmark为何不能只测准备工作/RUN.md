# 第 31 章完整累计工程独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

准备固定 Go 1.27.1 linux/amd64、PostgreSQL 16.15、可访问的模块镜像。仓库演示脚本 `writing-plans/go-language/scripts/verify31.sh` 会在新目录、新临时数据库、新 GOMODCACHE 和 GOCACHE 下实际解包执行；以下命令也可手动执行。`trust` 仅限本机 loopback 临时数据库，不可用于正式环境。

```bash
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-31-reader.XXXXXX)
tar -C "$reader" -xzf go-language-31.tar.gz
pgdata=$(mktemp -d /tmp/go-language-31-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-31-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-31-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
go test -count=1 -run '^FuzzCountWordsMatchesFields$|^TestCountWordsMatchesFields$' -v ./stats
go test -run '^$' -fuzz='^FuzzCountWordsMatchesFields$' -fuzztime=3s -parallel=1 -timeout=90s ./stats
go test -run '^$' -bench '^BenchmarkTask' -benchmem -benchtime=200ms -count=5 ./...
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

CLI 零期限预期退出 2，其他命令退出 0。原始 `.command/.stdout/.stderr/.exit` 在归档的 `go-language/evidence/31/`，优化前基准也在其中。fuzz 是有限预算；无反例不证明正确。全量 SQL 回归需使用真实 DSN，未配置时部分集成测试会 SKIP，不能算作 SQL 验收。页面下载不代替实验。
