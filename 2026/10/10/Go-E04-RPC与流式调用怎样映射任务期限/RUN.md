# Go E04：真实 gRPC + PostgreSQL 独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先在空目录执行 `sha256sum -c SHA256SUMS`、`tar -xzf go-language-E04.tar.gz`，进入 `go-language`。Go 1.27.1/linux-amd64、`CGO_ENABLED=1`、PostgreSQL 16、`curl` 和本地 C 编译器可用；设置 `GOTOOLCHAIN=local GOWORK=off` 及固定 Go 1.27.1 的 `PATH`。执行 `go mod download`、`go mod verify`、`sha256sum -c evidence/E04/source-sha.stdout`，核对 `go list -m google.golang.org/grpc` 为 `v1.67.1`。

在全新临时目录执行 `initdb -D "$PGDATA" -A trust -U admin --no-instructions`，用 `pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start` 启动隔离 loopback PostgreSQL，设置 `GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=postgres sslmode=disable"`。运行 `bash verification/E04.sh "$(mktemp -d)"`：脚本禁止 SQL 场景 SKIP，真实 gRPC 十轮提交/流取消/服务退出/SQL 终态及正常流/错误 ID。再执行 `go test -count=1 ./...`、`go test -race -count=1 ./...`、`go build -o taskstats .`，最后停掉实验库。

仓库层复跑入口 `writing-plans/go-language/scripts/verify-next.sh E04 'RPC与流式调用怎样映射任务期限'` 会新建数据库、新双缓存并保存原始 `unpack-*`。页面/下载检查只能验收站点链接，不能代替上述 TCP/gRPC/SQL 证据。JSON codec 仅用于此实验，不要用默认 protobuf 客户端直接发起 RPC。
