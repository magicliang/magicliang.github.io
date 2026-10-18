# 第 34 章累计工程独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

需要 Go 1.27.1 linux/amd64（与源文件 SHA 对应）、PostgreSQL 16.15 和模块镜像。仓库 `writing-plans/go-language/scripts/verify-next.sh 34 goroutine等待时调度器看到了什么` 在新工程目录、临时 loopback 数据库与新缓存运行并保存双流/退出码。`trust` 不可用于正式数据库。

```bash
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-34-reader.XXXXXX)
tar -C "$reader" -xzf go-language-34.tar.gz
pgdata=$(mktemp -d /tmp/go-language-34-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-34-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-34-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
sha256sum -c evidence/34/source-files.stdout
go test -count=10 -run '^TestWorkerWaitKinds$' -v .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

零期限 CLI 命令预期退出 2，其他命令应为 0。阶段状态取自实际 goroutine 栈，G 状态不等于 M/P 状态；待释放任务仍是 RUNNING，须等 `Close` 和终态确认。章节测试里的 TCP 仅为本机 loopback；真正 SQL 路径由累计测试中有 DSN 的场景验证，无 DSN 的 SKIP 不能充数。页面生成与下载不代替 Go/SQL 实验。
