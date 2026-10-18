# 17 素材包独立验收

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-17.tar.gz` 内含当前唯一累计工程、`README.md`、`RUN.md`、`VERSIONS.md`、前章与本章的文本实验命令/退出码/原始双流；此前 HTTP 归档下载的大型二进制不嵌套打包，仍在原章素材目录。先以 `sha256sum -c SHA256SUMS` 验证，再解包到自行创建的独立目录，进入 `go-language/`：

```sh
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=0
go version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=50 -run 'TestCancellationUnblocksFullSendAndEmptyReceive|TestCancelRequestWaitsForWorkerExit|TestDeadlineReturnsClassifiedError|TestAnalyzeContextCancellationBetweenRunes' ./...
go build -o /tmp/go-language-17-unpacked-taskstats .
/tmp/go-language-17-unpacked-taskstats --text 'Go 写 Go'
/tmp/go-language-17-unpacked-taskstats --batch 'Go|one two'
/tmp/go-language-17-unpacked-taskstats --text 'Go 写 Go' --timeout 0s
/tmp/go-language-17-unpacked-taskstats --text 'Go 写 Go' --timeout 1h
```

本目录 `unpack-*` 是**实际**新建临时目录解包后记录的每条命令、原始双流及退出码，`unpack-environment.txt` 含解包路径与工具环境。`--timeout 0s` 直接运行的 CLI 退出 2 是有意测试截止错误，不是编译失败；若改用 `go run`，外层工具的退出码可能与程序退出码不同。本轮没有运行 race、HTTP、SQL、其他平台或发布。
