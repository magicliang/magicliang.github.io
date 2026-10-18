# 08 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

运行 `sha256sum -c SHA256SUMS`，解包 `go-language-08.tar.gz` 后进入 `go-language/`，按 `VERSIONS.md` 与 `RUN.md` 检查工具链并复跑。归档内是截至 08 的完整累计工程、当章 08 原始证据及早期章节除 HTTP 下载二进制外的原始 Go 证据；早期的 HTTP 下载内容保存在各自正文素材目录。

`testdata/nonaddressable-receiver.go` 是预期编译失败的独立文件，不属于主 module 的正常构建；不要将其失败退出码混入 `go test ./...` 的通过结果。`unpack-*` 保存本章归档实际校验、解包、测试、构建与正反 CLI 路径的结果。
