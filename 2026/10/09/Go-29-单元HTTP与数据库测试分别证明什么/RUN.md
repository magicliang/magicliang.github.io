# 29 完整工程包：独立三层测试与数据库清理

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-29.tar.gz` 包含 00–29 的同一个任务服务、依赖版本、研究卡与原始测试记录，不嵌套旧章归档。先 `sha256sum -c SHA256SUMS`，然后在**新工程目录、新 PostgreSQL 16 数据目录、新 Go 模块缓存**复跑；本仓库 `writing-plans/go-language/scripts/verify29.sh` 把实际命令、stdout、stderr、退出码写在本素材目录 `unpack-*`。

```sh
reader=$(mktemp -d /tmp/go-language-29-reader.XXXXXX)
tar -C "$reader" -xzf go-language-29.tar.gz
pgdata=$(mktemp -d /tmp/go-language-29-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-29-modcache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
env -u GO_LANGUAGE_SQL_DSN go test -count=1 -run '^TestTaskInputAcrossUnitHTTPAndPostgreSQL$' -v .
go mod verify
go mod tidy -diff
go test -count=1 -run 'TestTaskInputAcrossUnitHTTPAndPostgreSQL|TestHTTPBlankInputRejectedBeforeSQL' -v .
go test -count=10 -run 'TestTaskInputAcrossUnitHTTPAndPostgreSQL|TestHTTPBlankInputRejectedBeforeSQL' -v .
psql -h 127.0.0.1 -p "$port" -U admin -d postgres -Atc "SELECT count(*) FROM pg_database WHERE datname LIKE 'go_task_29_%'"
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

无 DSN 的第一组预期 SQL 子测试 **SKIP**，命令仍退出 0；这不是 SQL 验收，必须核对后来真实库的 PASS 与清理剩余 0。CLI 零期限的应用进程预期退出 2，其他命令预期 0。`trust` 只在 loopback 实验数据库启用；测试身份需可创建和删除数据库。HTTP 页面与压缩包下载检查不能代替三层实验。
