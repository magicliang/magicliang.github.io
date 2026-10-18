# 27 完整工程包：独立复跑池等待与 SQL 取消

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-27.tar.gz` 是 00–27 单一累计工程、冻结版本、研究卡与实验双流记录，不嵌套旧包。先在同目录 `sha256sum -c SHA256SUMS`，再在空目录解包；必须使用实际运行的 PostgreSQL 16（本地隔离数据目录）和 Go 1.27.1，不能用没有 DSN 的 Skip 充数。仓库脚本 `writing-plans/go-language/scripts/verify27.sh` 会创建新工程目录、新 PostgreSQL 数据目录和新 Go 模块缓存，依次执行下面的命令并把命令、双流与退出码写到本素材目录的 `unpack-*` 中：

```sh
reader=$(mktemp -d /tmp/go-language-27-reader.XXXXXX)
tar -C "$reader" -xzf go-language-27.tar.gz
pgdata=$(mktemp -d /tmp/go-language-27-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-27-modcache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
go test -count=1 -run 'TestSQLHTTPPoolWaitDeadlineAndRecovery|TestSQLDriverQueryDeadlineAndRecovery' -v .
go test -count=20 -run 'TestSQLHTTPPoolWaitDeadlineAndRecovery|TestSQLDriverQueryDeadlineAndRecovery' -v .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

CLI 零期限的**应用进程**预期退出 2，其余命令退出 0。`trust` 仅供临时目录的 loopback 实验，不用于共享数据库。复制包里的源码与证据可复核结论，但静态 HTML 的 200 不代替 SQL 复跑；未知提交结果、外部副作用去重和跨平台结果仍 `NOT_RUN`。
