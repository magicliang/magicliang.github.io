# 28 完整工程包：独立复跑进程崩溃与重启

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-28.tar.gz` 包含同一任务服务的 00–28 累计代码、固定版本、研究卡和原始证据，不嵌套旧包。在新目录解包，并使用独立 PostgreSQL 16 数据目录、新 Go 模块缓存运行；本仓库脚本 `writing-plans/go-language/scripts/verify28.sh` 记录以下步骤实际命令、stdout、stderr 与退出码到本素材目录 `unpack-*`。

```sh
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-28-reader.XXXXXX)
tar -C "$reader" -xzf go-language-28.tar.gz
pgdata=$(mktemp -d /tmp/go-language-28-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-28-modcache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
go test -count=1 -run 'TestSQLProcessCrashAndRecovery|TestSQLRecoveryUpgradesPriorSchema' -v .
go test -count=15 -run 'TestSQLProcessCrashAndRecovery|TestSQLRecoveryUpgradesPriorSchema' -v .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

CLI 零期限**程序**退出码预期为 2；其余命令退出 0。`trust` 仅适用于本机隔离的 loopback 数据库。子进程杀死后不能调用 `Close` 来伪装真实崩溃；测试必须报告信号退出并从 SQL 查到旧 RUNNING。页面 200 不能代替真实进程/SQL 实验；数据库自身崩溃、生产恢复编排、跨实例租约和外部副作用去重 `NOT_RUN`。
