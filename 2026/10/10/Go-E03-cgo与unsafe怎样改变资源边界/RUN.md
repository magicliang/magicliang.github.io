# Go E03：独立构建与失败输入

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先执行 `sha256sum -c SHA256SUMS`、`tar -xzf go-language-E03.tar.gz`，进入全新解包目录 `go-language`。要求 Go 1.27.1/linux-amd64、`gcc 13.3.0` 或记录实测兼容编译器、`CGO_ENABLED=1`、`GOTOOLCHAIN=local`、`GOWORK=off`。`sha256sum -c evidence/E03/source-sha.stdout` 后运行 `bash verification/E03.sh "$(mktemp -d)"`；真正编译 cgo 二进制、十次执行错误输入/正常求和、十次运行原 HTTP 服务成功/失败终态，另记录 `CGO_ENABLED=0 go test ./native` 的非零退出。

为累计 SQL 回归单独启动 loopback trust PostgreSQL 16：`initdb -D "$PGDATA" -A trust -U admin --no-instructions`，`pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start`，设置 `GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=postgres sslmode=disable"`，再运行 `go mod verify`、`go test -count=1 ./...`、`go test -race -count=1 ./...`、`go build -o taskstats .`。关闭本轮数据库，勿对生产实例操作。仓库层脚本 `writing-plans/go-language/scripts/verify-next.sh E03 'cgo与unsafe怎样改变资源边界'` 会新建 PostgreSQL、隔离双缓存并留下 `unpack-*` 原始证据；页面检查不替代 native/SQL 实验。
