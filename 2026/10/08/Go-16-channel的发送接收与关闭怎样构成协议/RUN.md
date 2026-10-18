# 16 素材包解包与复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-16.tar.gz` 内含截至 16 的同一累计工程、版本及复跑说明（`README.md`、`RUN.md`、`VERSIONS.md`）、文本实验的命令/双流/退出码。过去章节的网站归档 HTTP 下载二进制不嵌套打包；它们各自保留在原章素材目录。先验 SHA-256，再解包到独立临时目录：

```sh
sha256sum -c SHA256SUMS
tar -xzf go-language-16.tar.gz -C /tmp/GO-16-NEW-DIR
cd /tmp/GO-16-NEW-DIR/go-language
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=0
go version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=30 -run 'TestQueueDrainsBeforeReturning|TestQueueEmptyInputTerminates|TestChannelEmptyFullNilAndClosed' .
go build -o /tmp/go-language-16-unpacked-taskstats .
go build -o /tmp/go-language-16-unpacked-closed ./testdata/send-after-close.go
/tmp/go-language-16-unpacked-closed
/tmp/go-language-16-unpacked-taskstats --batch 'Go|one two'
/tmp/go-language-16-unpacked-taskstats --batch 'Go|'
```

路径 `/tmp/GO-16-NEW-DIR` 是读者自行创建的示意位置，不是本次执行命令；实际解包临时路径、命令、原始输出及退出码在本素材目录的 `unpack-*` 文件中。`unpack-closed` 退出 2 是反例 panic，不要把它计为正常工程的故障；空文本退出 2 是业务校验。本轮未运行其他平台、race、HTTP 或 SQL。
