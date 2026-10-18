# 18 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-18.tar.gz` 是 18 章的完整累计工程（含 `README.md`、`RUN.md`、`VERSIONS.md`、前章/本章文本实验命令、双流和退出码；前章 HTTP 归档的二进制保留在各自素材目录，不再嵌套复制）。先 `sha256sum -c SHA256SUMS`，实际创建独立目录后解包，进入其中的 `go-language/`，确认以下本机条件再运行：

```sh
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1
go version
gcc --version
go mod tidy -diff
go test -count=1 -v ./...
TASKSTATS_UNSAFE_RACE=1 go test -race -count=1 -run '^TestStoreRaceScenario$' -v .
go test -race -count=1 -run '^TestStoreRaceScenario$' -v .
go test -race -count=1 -v ./...
go build -o /tmp/go-language-18-unpacked-taskstats .
/tmp/go-language-18-unpacked-taskstats --batch 'Go|one two'
/tmp/go-language-18-unpacked-taskstats --text 'Go 写 Go' --timeout 0s
```

其中带 `TASKSTATS_UNSAFE_RACE=1` 的那一条**应当报告 DATA RACE 并退出非零**；它只切换独立测试替身，正常程序和后续 `go test -race` 不需要此变量。`unpack-*` 包含本章真实解包目录、实际执行命令、原始双流和退出码；不是列举“预计结果”。有锁路径这一次无报告不是全路径安全证明。没有运行 SQL、HTTP、其他平台或发布。
