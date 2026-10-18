# Go E02 独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`sha256sum -c SHA256SUMS`，`tar -xzf go-language-E02.tar.gz`，进入全新解包的 `go-language`。工具链固定 Go 1.27.1/linux-amd64，设置 `GOTOOLCHAIN=local`、`GOWORK=off`、`PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH`；需要 `go`、`rg`、`cmp`、`sha256sum`、`psql`、PostgreSQL 16。

先执行 `sha256sum -c evidence/E02/source-sha.stdout` 和 `bash verification/E02.sh "$(mktemp -d)"`。脚本真正执行生成、与提交产物逐字节比较、坏 schema 非零退出且不写产物、十轮有效/错误输入测试与五轮 benchmark；不能只读取已打包输出。再独立新建 loopback trust PostgreSQL：`initdb -D "$PGDATA" -A trust -U admin --no-instructions`，`pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start`，设置 `GO_LANGUAGE_SQL_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=postgres sslmode=disable"`，执行 `go mod verify`、`go test -count=1 ./...`、`go test -race -count=1 ./...`、`go build -o taskstats .`，最后停止本轮数据库。

仓库内 `writing-plans/go-language/scripts/verify-next.sh E02 '反射与代码生成如何校验任务字段'` 自动建新数据库、隔离 Go 双缓存再复跑；`unpack-*` 是实际解包记录。Hexo 页面/下载检查另算，不能代替生成与 SQL 实验。
