# Go 39：在空目录独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先执行 `sha256sum -c SHA256SUMS`、`tar -xzf go-language-39.tar.gz`、`cd go-language`。需要 Go 1.27.1 linux/amd64、PostgreSQL 16 (`initdb`、`pg_ctl`、`psql`)、`python3`、`curl`、`rg`、`sha256sum`，实验只绑定 loopback trust，严禁在真实数据库上运行。

设置 `PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH`、`GOTOOLCHAIN=local`、`GOWORK=off` 和 `GO_LANGUAGE_SQL_DSN='host=127.0.0.1 port=<独立端口> user=admin dbname=postgres sslmode=disable'`。在一个**全新临时目录**里执行 `initdb -D "$PGDATA" -A trust -U admin --no-instructions`，再执行 `pg_ctl -D "$PGDATA" -o "-h 127.0.0.1 -p $PGPORT -k $PGDATA" -l "$PGDATA/server.log" start`。核对 `go version`、`psql -h 127.0.0.1 -p "$PGPORT" -U admin -d postgres -Atc 'select version()'`、`go mod verify` 和 `sha256sum -c evidence/39/source-sha.stdout`。

接着运行 `go test -count=1 ./...`、`go test -race -count=1 ./...`、`go build -trimpath -o taskstats .`、`go version -m ./taskstats`；执行 `psql -h 127.0.0.1 -p "$PGPORT" -U admin -d postgres -c 'CREATE DATABASE go39live'` 后，设置 `GO_LANGUAGE_SERVE_DSN="host=127.0.0.1 port=$PGPORT user=admin dbname=go39live sslmode=disable"`，运行 `bash verification/39.sh "$(pwd)/taskstats" "$(mktemp -d)"`。脚本依次运行正常、非法输入、过载、取消、数据库失败、退出与崩溃重启，会在传入的证据目录留完整命令/双流/退出码、任务 ID、HTTP body 和 SQL 终态；若任一断言失败，**本轮不计入验收**。运行结束停止专属 PostgreSQL：`pg_ctl -D "$PGDATA" -m fast stop`。

仓库层还可执行 `writing-plans/go-language/scripts/verify-next.sh 39 '空环境如何验收任务完整生命周期'`：它自动新建数据库、隔离模块和编译缓存，重跑全包、race、受控 SQL 测试和真实进程矩阵；解包复跑证据为素材目录内的 `unpack-*`。网站的页面/下载检查是另一项验收，不能替代上面的 Go/SQL 实验。首次崩溃试跑的失败证据在包内 `evidence/39/pilot-restart-sleep/`，不要删除。
