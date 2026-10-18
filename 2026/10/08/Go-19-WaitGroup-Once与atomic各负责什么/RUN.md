# 19 归档解包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

`go-language-19.tar.gz` 保留本章完整累计工程及 `README.md`、`RUN.md`、`VERSIONS.md`、此前各章文本实验的原始命令/双流/退出码。前章 HTML 下载二进制不嵌套打包，保留在原各篇素材目录。先验证 `sha256sum -c SHA256SUMS`，再解包到**新建的独立目录**，进入解出的 `go-language/` 运行：

```sh
export PATH=/tmp/go-language-toolchain-1.27.1/go/bin:$PATH
export GOTOOLCHAIN=local GOWORK=off GOMAXPROCS=2 CGO_ENABLED=1
go version
gcc --version
go mod tidy -diff
go test -count=1 -v ./...
go test -count=40 -run 'TestSettingsOnceInitializesForConcurrentCallers|TestStoreRaceScenario|TestIndependentAtomicCountDoesNotPublishResult|TestCancelRequestWaitsForWorkerExit' -v .
TASKSTATS_UNSAFE_RACE=1 go test -race -count=1 -run '^TestStoreRaceScenario$' -v .
go test -race -count=1 -run '^TestStoreRaceScenario$' -v .
go test -race -count=1 -v ./...
go build -o /tmp/go-language-19-unpacked-taskstats .
/tmp/go-language-19-unpacked-taskstats --batch 'Go|one two'
/tmp/go-language-19-unpacked-taskstats --batch 'Go|'
```

`unpack-*` 为本次真实解包、测试、构建及二进制复跑的命令、双流、退出码，`unpack-environment.txt` 有具体目录和 Go/GCC 环境。故意无锁的测试替身即使有原子计数，也应实际出现 `WARNING: DATA RACE`，退出 1；该命令不代表正常测试失败。原子终态数不能取代多字段状态快照的 Mutex。任务服务 SQL/HTTP、其他平台与发布均未运行。
