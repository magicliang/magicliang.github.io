# 24 完整工程包：解包复跑出站请求

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-24.tar.gz` 包含累计 Go 工程、测试、版本/运行文档与 00–24 原始文本证据（不嵌套旧章可下载包）。在本素材目录校验摘要，再解包到新的目录：

```sh
sha256sum -c SHA256SUMS
mkdir -p /tmp/go-language-24-reader
tar -C /tmp/go-language-24-reader -xzf go-language-24.tar.gz
cd /tmp/go-language-24-reader/go-language
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1
go version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=20 -run 'TestDownstream|TestTaskCancelInterruptsDownstream' -v .
go test -race -count=1 ./...
go build -o /tmp/go-language-24-reader-taskstats .
/tmp/go-language-24-reader-taskstats --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
/tmp/go-language-24-reader-taskstats --text Go --timeout 0s --workers 2
```

最后的零期限 CLI 预期退出 2，其余命令预期退出 0；合成下游仍会通过本地 loopback TCP 实际请求。`unpack-*` 保存本次独立解包命令、原始双流和退出码。真实 OS 黑洞 TCP 拨号、长期资源增长、真实 SQL、其他平台和发布 `NOT_RUN`；本机无 race 报告只覆盖执行路径。
