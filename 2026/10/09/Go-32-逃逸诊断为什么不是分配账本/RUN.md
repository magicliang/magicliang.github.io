# 第 32 章累计工程独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

需要固定 Go 1.27.1 linux/amd64、PostgreSQL 16.15，模块镜像可达。仓库 `writing-plans/go-language/scripts/verify-next.sh 32 逃逸诊断为什么不是分配账本` 将在新工程目录、隔离数据库、新 GOMODCACHE 和 GOCACHE 实际执行这些步骤并记录原始双流与退出码。`trust` 仅用于临时 loopback 数据库。

```bash
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-32-reader.XXXXXX)
tar -C "$reader" -xzf go-language-32.tar.gz
pgdata=$(mktemp -d /tmp/go-language-32-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-32-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-32-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
cp -a "$reader/go-language" "$reader/old-go-language"
cp evidence/32/old-source.stdout "$reader/old-go-language/stats/count.go"
(cd "$reader/old-go-language" && go build -gcflags='example.com/go-language-task/stats=-m=2' ./stats)
go build -gcflags='example.com/go-language-task/stats=-m=2' ./stats
go test -run '^$' -bench '^BenchmarkTask(CountWords|FieldsReference)$' -benchmem -benchtime=200ms -count=5 ./stats
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

旧实现来源固定为 `351b838365057d66f7a845801469bc267ddb4055`；归档内 `evidence/32/old-source.stdout` 即记录的旧文件原文，复跑不依赖本地 Git 历史。旧 CLI 的零期限命令预期退出 2，其余为 0。SQL 测试需要真实 DSN，否则跳过集成路径不能计作通过。没有 race 报告不能推断全路径安全；页面下载不能替代诊断与测试。
