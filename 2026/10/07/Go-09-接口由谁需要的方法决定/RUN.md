# 09 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

执行 `sha256sum -c SHA256SUMS` 后解包 `go-language-09.tar.gz`，进入 `go-language/`；按 `VERSIONS.md` 冻结的环境使用 `RUN.md` 运行主工程与隔离反例。归档包含截至 09 的唯一累计工程、09 当章完整 Go 证据及较早章节除 HTTP 下载二进制外的命令与原始 Go 证据；历史 HTTP 原始下载正文仍留在相应正文素材目录。

`testdata/interface-value-error.go` 是预期编译失败的短程序，本机退出 1；正常两包 `go test ./...` 不编译它。`unpack-*` 记录本章实际校验、解包、构建、测试、正反查询及编译反例的双流和退出码。
