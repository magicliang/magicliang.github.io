# 第 35 章累计工程独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

固定 Go 1.27.1 linux/amd64、PostgreSQL 16.15、可达模块镜像；仓库 `writing-plans/go-language/scripts/verify-next.sh 35 profile如何定位热点而不替代测量` 会在新目录、新 loopback 数据库和新模块/构建缓存解包独立复跑并保存原始双流和退出码。

```bash
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-35-reader.XXXXXX)
tar -C "$reader" -xzf go-language-35.tar.gz
pgdata=$(mktemp -d /tmp/go-language-35-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-35-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-35-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
cp -a "$reader/go-language" "$reader/old-go-language"
cp evidence/35/old-source.stdout "$reader/old-go-language/stats/count.go"
(cd "$reader/old-go-language" && go test -run '^$' -bench '^BenchmarkTask(AnalyzeContext|HTTPRead)$' -benchmem -benchtime=200ms -count=5 .)
go test -run '^$' -bench '^BenchmarkTask(AnalyzeContext|HTTPRead)$' -benchmem -benchtime=200ms -count=5 .
go test -run '^$' -bench '^BenchmarkTask(AnalyzeContext|HTTPRead)$' -benchtime=1s -cpuprofile="$reader/cpu-35.pprof" -memprofile="$reader/heap-35.pprof" -memprofilerate=1024 .
go tool pprof -top -nodecount=20 "$reader/cpu-35.pprof"
go tool pprof -alloc_space -top -nodecount=20 "$reader/heap-35.pprof"
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

`-cpuprofile` 会在当前目录留下 `go-language-task.test`，复跑脚本在确认 profile 已读取后删除该编译产物；它不是归档的一部分。零期限 CLI 预期退出 2，其余命令退出 0。采样导致计时扰动，正常 benchmark 与 profile 分开解释；SQL 全量回归必须有真实 DSN，跳过 SQL 的测试不算真库通过。`trust` 只用于本机临时实例；页面下载不代替 Go/SQL 实验。
