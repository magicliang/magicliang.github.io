# 12 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

执行 `sha256sum -c SHA256SUMS`，解包 `go-language-12.tar.gz`，从包内 `go-language/` 的 `VERSIONS.md` 和 `RUN.md` 读取复跑命令。归档包含 12 当章包括失败前/修复后在内的原始 Go 证据与完整累计工程；前章 HTTP 下载二进制不重复打包，原始件仍在对应博文素材目录。

`testdata/recover-outside-defer.go` 是刻意保留的未处理 panic，编译二进制后本机退出 2；`panic_test.go` 正向恢复发生在同一 goroutine 的测试调用栈，不是生产 CLI 的全局 recover。`unpack-*` 保存本素材实际解包后的测试、构建、正反程序运行命令、双流及退出码。
