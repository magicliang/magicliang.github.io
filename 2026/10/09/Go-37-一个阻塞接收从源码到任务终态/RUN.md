# 第 37 章完整累计工程独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

冻结 Go 1.27.1 linux/amd64 与源码文件 SHA、PostgreSQL 16.15、可用模块镜像。`writing-plans/go-language/scripts/verify-next.sh 37 一个阻塞接收从源码到任务终态` 在新目录、新 PostgreSQL、新双缓存中解包、核对实际源码文件哈希、重跑两种唤醒与真库回归。`trust` 仅用于本地临时实例。

```bash
sha256sum -c SHA256SUMS
reader=$(mktemp -d /tmp/go-language-37-reader.XXXXXX)
tar -C "$reader" -xzf go-language-37.tar.gz
pgdata=$(mktemp -d /tmp/go-language-37-pg.XXXXXX)
port=$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')
/usr/lib/postgresql/16/bin/initdb -D "$pgdata" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -o "-h 127.0.0.1 -p $port -k $pgdata" -l "$pgdata/server.log" start
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1 GOPROXY=https://goproxy.cn
export GOMODCACHE=$(mktemp -d /tmp/go-language-37-modcache.XXXXXX)
export GOCACHE=$(mktemp -d /tmp/go-language-37-gocache.XXXXXX)
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$port user=admin dbname=postgres sslmode=disable"
cd "$reader/go-language"
go version
go mod download github.com/lib/pq@v1.12.3
go mod verify
go mod tidy -diff
sha256sum -c evidence/37/source-sha.stdout
go test -count=10 -run '^TestChannelWakeAndWorkerExit$' -v .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o "$reader/taskstats" .
"$reader/taskstats" --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
"$reader/taskstats" --text Go --timeout 0s --workers 2
/usr/lib/postgresql/16/bin/pg_ctl -D "$pgdata" -m fast stop
```

零期限 CLI 预期退出 2，其他命令应为 0。源码哈希核对只保证本机所安装文件与记录相同；tag Git SHA 来自镜像，官方 Gitiles 独立核验仍 `NOT_RUN`。实验 release 闸门关闭不等于 context 取消、HTTP 202 不等于 worker 终态；SQL 集成测试必须有实际 DSN，否则 Skip 不能充数。页面下载不代替 Go/SQL 路径。
