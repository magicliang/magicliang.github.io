# 25 完整工程包：真实 PostgreSQL 独立解包

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-25.tar.gz` 包含截至 25 的累计工程、测试、版本文档、00–25 研究卡及原始文本证据（旧章压缩包不再嵌套）。先校验，再用**新的**目录解包；SQL 测试要求读者自己在隔离目录运行 PostgreSQL 16，不依赖作者本次的 `/tmp` 路径：

```sh
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-25-reader.XXXXXX)
tar -C "$reader" -xzf go-language-25.tar.gz
pgdata=$(mktemp -d /tmp/go-language-25-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
psql -h 127.0.0.1 -p "$port" -U admin -d postgres -Atc 'select version()'
cd "$reader/go-language"
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
go version
go mod verify
go mod tidy -diff
go test -count=15 -run 'TestSQL' -v .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

CLI 零期限预期退出 2，其余命令预期退出 0；`unpack-*` 保存本次实际另启数据库与归档复跑的命令、原始 stdout/stderr、退出码。只在 loopback 且临时隔离目录使用 `trust`；不要将此鉴权配置用于共享数据库。SQL 目前只写入 QUEUED，HTTP 终态仍来自内存；不把本篇写成跨进程恢复或外部下游副作用已完成。其他平台、全站构建与发布 `NOT_RUN`。
