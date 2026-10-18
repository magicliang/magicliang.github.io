# 13 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先运行 `sha256sum -c SHA256SUMS`，解包 `go-language-13.tar.gz` 后从 `go-language/` 目录阅读 `VERSIONS.md`、`RUN.md`。包内包含当前完整累计工程、本章包括两个编译失败样例的 Go 原始证据，以及前章除 HTTP 下载二进制外的原始命令与文本证据；前章 HTTP 原件留在各篇素材目录。

`testdata/invalid-summarizer.go` 和 `invalid-type-operation.go` 应分别编译失败，本机退出 1；正常 `go test ./...` 不包含二者。`unpack-*` 是该归档独立解包后真正校验、构建、测试及正反 CLI 复跑的原始输出。
