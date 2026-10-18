# 20 完整归档解包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-20.tar.gz` 包含截至第 20 章的同一累计 Go 工程、`README.md`、`RUN.md`、`VERSIONS.md`，以及 00–20 的文本证据（不嵌套此前章节的二进制下载包）。`SHA256SUMS` 对应本章压缩包。先核对摘要，再解包到新的空目录。进入其中的 `go-language/` 后运行：

```sh
sha256sum -c SHA256SUMS
mkdir -p /tmp/go-language-20-reader
tar -C /tmp/go-language-20-reader -xzf go-language-20.tar.gz
cd /tmp/go-language-20-reader/go-language
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1
go version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=50 -run 'TestBoundedPool|TestCLIWorkerAndQueueLimits' -v .
go test -race -count=1 ./...
go build -o /tmp/go-language-20-reader-taskstats .
/tmp/go-language-20-reader-taskstats --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
/tmp/go-language-20-reader-taskstats --text Go --workers 0
```

受控测试中的第二次满队列提交应返回 `ErrQueueFull`，取消闸门要等 worker 真正退出才允许返回；CLI `--workers 0` 预期退出 2，stdout 空。`unpack-*` 保存本次在另外创建的独立目录里真正运行上述命令的原始双流与退出码；机器架构、编译器、Go 二进制来源与 tag/SHA 见包内 `VERSIONS.md` 和 evidence。`go test -race` 的无报告只对执行到的路径有效。此包只验证进程内批次，HTTP/SQL/其他平台/发布 `NOT_RUN`。
