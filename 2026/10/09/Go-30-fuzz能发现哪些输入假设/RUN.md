# 30 完整工程包：独立复跑输入与状态序列 fuzz

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-30.tar.gz` 含同一任务服务的 00–30 累计源码、冻结版本、研究卡与原始实验，不嵌旧章包。先用 `sha256sum -c SHA256SUMS` 对照；仓库脚本 `writing-plans/go-language/scripts/verify30.sh` 在**新工程目录、新 PostgreSQL 16 数据目录、新模块缓存及新 Go 构建/模糊语料缓存**实跑并在本素材目录保存 `unpack-*` 的命令、stdout、stderr、退出码。

```sh
reader=$(mktemp -d /tmp/go-language-30-reader.XXXXXX)
tar -C "$reader" -xzf go-language-30.tar.gz
pgdata=$(mktemp -d /tmp/go-language-30-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-30-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-30-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
go test -count=1 -run '^FuzzHTTPTaskSubmission$|^FuzzTaskStateSequence$' -v .
go test -run '^$' -fuzz='^FuzzHTTPTaskSubmission$' -fuzztime=3s -parallel=1 -timeout=90s .
go test -run '^$' -fuzz='^FuzzTaskStateSequence$' -fuzztime=3s -parallel=1 -timeout=90s .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

CLI 零期限的应用程序预期退出 2，其他命令退出 0；fuzz 数量每次可能不同，**未失败不证明正确**。SQL 全量回归需要真实 DSN，空 DSN 会 Skip；fuzz 目标自身只走 in-memory HTTP 响应录制器和顺序状态逻辑，不代表 SQL 已 fuzz。`trust` 仅用于 loopback 临时数据库；页面下载不能代替 Go fuzz 或真 SQL 实验。
