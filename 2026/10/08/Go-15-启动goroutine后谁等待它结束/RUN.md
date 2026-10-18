# 15 素材包独立复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

本目录的 `go-language-15.tar.gz` 是第 15 章的**完整累计工程快照**（含 `README.md`、`RUN.md`、`VERSIONS.md`、前章和本章的文本实验命令、双流及退出码；前章网站下载的大型二进制不递归打包，仍在各章素材目录）。先用 `sha256sum -c SHA256SUMS` 验证，再 `tar -xzf go-language-15.tar.gz`；进入解出的 `go-language/`，而不是当前仓库的 `examples/go-language/`，运行：

```sh
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=0
go version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=30 -run 'TestAsyncWaitsForWorkBeforePublishingResult|TestAsyncPreservesValidationErrors' .
go run ./testdata/async-without-wait.go
go build -o /tmp/go-language-15-unpacked-taskstats .
/tmp/go-language-15-unpacked-taskstats --batch 'Go|one two'
/tmp/go-language-15-unpacked-taskstats --batch 'Go|'
```

`unpack-*` 是本章在独立目录实际校验、解包和复跑的命令、原始双流、退出码；`unpack-environment.txt` 记录所在目录和环境。非本机安装 Go 1.27.1 时按 `VERSIONS.md` 取得相同 patch；其他 Go patch 的运行不冒充本章实测。`--batch 'Go|'` 的 2 是输入错误的预期码，反例 `async-without-wait.go` 的 0 仅表明教学程序正常执行，不代表“只确认启动”这种业务判断正确。
