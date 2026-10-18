# 23 完整工程包：解包复跑取消与退出

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-23.tar.gz` 是同一累计 Go 工程截至 23 的代码、测试、版本/运行文档与 00–23 的原始文本证据（不嵌套前章可下载包的二进制）。先在本素材目录执行 `sha256sum -c SHA256SUMS`，再解包进新的独立目录，进入 `go-language/`：

```sh
mkdir -p /tmp/go-language-23-reader
tar -C /tmp/go-language-23-reader -xzf go-language-23.tar.gz
cd /tmp/go-language-23-reader/go-language
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1
go version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=30 -run 'TestHTTPExplicitCancel|TestHTTPQueuedCancel|TestHTTPClientCancel' -v .
go test -race -count=1 ./...
go build -o /tmp/go-language-23-reader-taskstats .
/tmp/go-language-23-reader-taskstats --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
/tmp/go-language-23-reader-taskstats --text Go --timeout 0s --workers 2
```

`TestHTTP*` 使用真实 loopback TCP 与闸门：HTTP 主动取消 202 时 RUNNING 保留 CancelRequested、工作返回后才 CANCELED；排队项立即取消且不启动分析器；客户端 202 后撤销自己的请求不取消任务，实际 HTTP `Server.Shutdown` 返回不替代业务执行器 `Close` 的等待。零期限 CLI 预期退出 2，不能当构建失败。本素材目录 `unpack-*` 保存这次真实独立解包的原始命令、双流和退出码。其他平台、持久 HTTP 监听、真实 SQL 与发布 `NOT_RUN`，本机 race 无报告只限所跑路径。
