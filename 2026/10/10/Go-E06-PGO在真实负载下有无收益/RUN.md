# Go E06：固定环境内的 PGO 负载复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先 `sha256sum -c SHA256SUMS`，在全新目录 `tar -xzf go-language-E06.tar.gz` 并进入 `go-language`。设置 Go 1.27.1/linux-amd64、`GOTOOLCHAIN=local`、`GOWORK=off`、`CGO_ENABLED=1`，运行 `go mod download`、`go mod verify`、`sha256sum -c evidence/E06/source-sha.stdout`。执行 `bash verification/E06.sh "$(mktemp -d)"`：重新采至少三秒 CPU profile，构建 `-pgo=off` 和 `-pgo=<真实 profile>` 两版二进制，分别启动真服务，在训练/未训练输入上交替各跑五轮，严格校验实际 ID/词数/终态与 SIGTERM 退出。输出并不要求 PGO 优于 off，负收益必须留在汇总与原始轮次中。

继续以独立 loopback trust PostgreSQL 16 执行累计 SQL 回归：`initdb -D "$PGDATA" -A trust -U admin --no-instructions`，`pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start`，设置 `GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=postgres sslmode=disable"`，运行 `go test -count=1 ./...`、`go test -race -count=1 ./...`，然后停止本轮数据库。

仓库入口 `writing-plans/go-language/scripts/verify-next.sh E06 'PGO在真实负载下有无收益'` 在新目录、SQL 和双缓存重复执行，素材目录内 `unpack-*` 为实测结果。此次 100 条任务测量是内存 HTTP、不是 SQL 性能；页面可下载不能替代 CPU/SQL 实验。
