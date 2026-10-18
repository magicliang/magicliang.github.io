# 06 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先执行 `sha256sum -c SHA256SUMS`，解包 `go-language-06.tar.gz`，进入包内 `go-language/`，核对 `VERSIONS.md` 中的工具链来源，然后使用 `RUN.md` 所列命令。包内附截至 06 的完整累计工程与 `evidence/00/` 至 `evidence/06/` 的 Go 原始日志。

`testdata/slice-alias-bug_test.go` 是故意失败的**独立反例**，不在正常 `go test ./...` 的扫描范围内。`unpack-*` 是本机对本章包独立解包后运行测试、二进制正反路径、失败夹具及两种 append 情况的实际记录；素材可用性也需单独检查 Hexo 生成与页面链接。
