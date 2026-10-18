# E08 双进程领取、崩溃与数据库效果去重

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

在素材目录核查 `sha256sum -c SHA256SUMS`，使用新的目标目录执行 `tar -xzf go-language-E08.tar.gz -C "$NEW_DIRECTORY"`；进入 `$NEW_DIRECTORY/go-language`。固定 Go 1.27.1、PostgreSQL 16.15、`GOTOOLCHAIN=local`、`GOWORK=off`、独立 `GOMODCACHE` 和 `GOCACHE`，执行 `go mod download`、`go mod verify` 及 `sha256sum -c evidence/E08/source-sha.stdout`。使用仅供实验的本地库，例如：

```sh
export PGDATA="$(mktemp -d /tmp/go-e08-reader-pg.XXXXXX)"
export PGPORT="$(python3 -c 'import socket; sock=socket.socket(); sock.bind(("127.0.0.1",0)); print(sock.getsockname()[1]); sock.close()')"
/usr/lib/postgresql/16/bin/initdb -D "$PGDATA" -A trust -U admin --no-instructions
/usr/lib/postgresql/16/bin/pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start
export GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=postgres sslmode=disable"
```

执行 `bash verification/E08.sh "$OUTPUT_DIRECTORY"`：它编译同一个服务的 `lease` CLI，实际 A 进程分别在领取后与效果事务提交后以非零码崩溃，B 在租约未过期时须领取失败，到期后用原任务 ID 重新领取；原始双流、各阶段实际 ID、带 epoch 的状态、效果表行数及 PostgreSQL 查询均须存档。再运行 `go test -count=10 -v -run '^TestLease' .`（包含过期实例效果/终态写入拒绝、两连接仅一个成功）、`go test -count=1 -v ./...`、`go test -race -count=1 ./...` 与旧 CLI 正反。不能只用页面检查或 HTTP 回应替代 SQL 实验。

实验完成后执行 `/usr/lib/postgresql/16/bin/pg_ctl -D "$PGDATA" -m fast stop`，不要复用本机已有数据库。效果表属于同一数据库的受控夹具，代表一条可去重的记录，未模拟外部服务中已成功但响应丢失的调用；外部动作、掉电与多主部署 `NOT_RUN`。原 `serve` 单实例恢复若与租约模式混跑会把 RUNNING 提前判 FAILED，因此**不要**混跑，也不把 E08 的受控两个 worker 称作生产服务的多实例支持。
