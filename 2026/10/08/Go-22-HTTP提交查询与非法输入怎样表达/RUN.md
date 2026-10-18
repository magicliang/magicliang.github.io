# 22 完整工程包：解包后真实 HTTP 复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-22.tar.gz` 含截至第 22 章的**同一累计工程**、`README.md`、`RUN.md`、`VERSIONS.md`、研究卡及 00–22 的原始文本证据，不嵌套前章 HTTP 下载的归档二进制。先在本素材目录运行 `sha256sum -c SHA256SUMS`，再解包到新建的独立目录，进入 `go-language/`：

```sh
mkdir -p /tmp/go-language-22-reader
tar -C /tmp/go-language-22-reader -xzf go-language-22.tar.gz
cd /tmp/go-language-22-reader/go-language
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1
go version
go mod tidy -diff
go test -count=1 -run '^TestHTTP' -v .
go test -count=20 -run '^TestHTTP' -v .
go test -count=1 -v ./...
go test -race -count=1 ./...
go build -o /tmp/go-language-22-reader-taskstats .
/tmp/go-language-22-reader-taskstats --batch 'Go|one two|Go' --workers 2 --queue-capacity 1
/tmp/go-language-22-reader-taskstats --text Go --workers 0
```

`TestHTTP*` 使用 `httptest.NewServer` 开真实 loopback HTTP 连接，断言 POST 202 时工作仍 RUNNING、解除闸门后成功，业务超词数后 FAILED，并覆盖 400/404/405/413/415/503。错误 worker 参数预期退出 2，不能算构建失败。本素材目录的 `unpack-*` 是此次真实解包复跑的命令、环境、原始 stdout/stderr 与退出码。此包尚无常驻 HTTP 监听 CLI；本章的 `httptest` 网络请求不等于发布 HTTP 服务、真实数据库或上线。无 race 报告只限执行过的路径；其他平台与发布 `NOT_RUN`。
