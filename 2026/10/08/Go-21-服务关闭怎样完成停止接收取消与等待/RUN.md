# 21 完整工程包：真正解包后复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-21.tar.gz` 含同一累计工程截至 21 的代码、测试、文档、研究卡和 00–21 的文本证据，不嵌套前章可下载二进制归档。先在素材目录运行 `sha256sum -c SHA256SUMS`，再解包到**新建**的独立目录，进入 `go-language/`：

```sh
mkdir -p /tmp/go-language-21-reader
tar -C /tmp/go-language-21-reader -xzf go-language-21.tar.gz
cd /tmp/go-language-21-reader/go-language
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1
go version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=100 -run 'TestExecutor|TestBoundedPool' -v .
go test -race -count=1 ./...
go build -o /tmp/go-language-21-reader-taskstats .
/tmp/go-language-21-reader-taskstats --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
/tmp/go-language-21-reader-taskstats --text Go --workers 0
go build -o /tmp/go-language-21-reader-negative ./testdata/send-after-close.go
/tmp/go-language-21-reader-negative
```

CLI 无效 worker 参数预期退出 2；故意向已关闭 channel 发送的独立二进制同样预期退出 2 且 stderr 包含 `send on closed channel`，与真实执行器的安全关闭测试相区分。素材目录 `unpack-*` 是本次在独立目录重跑的命令、原始双流和退出码。若没有冻结版 Go 1.27.1、本机受支持的 race 编译环境，不能将 `NOT_RUN` 写成通过；race 无报告不等于所有路径安全。HTTP/SQL 服务、其他平台和发布尚未运行。
