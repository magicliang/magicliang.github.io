# 04 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

在本素材目录先执行 `sha256sum -c SHA256SUMS`，将 `go-language-04.tar.gz` 解包，进入包内 `go-language/` 阅读 `VERSIONS.md` 与 `RUN.md`。本章在 00–03 累计代码上增加顺序批量 CLI；包内 `evidence/00/` 至 `evidence/04/` 是对应的原始 Go 实验记录。

素材目录 `unpack-*` 是这份归档在本机独立解包后真实测试、构建与正反路径的记录。不能把纯内存 stdout 暂存当作数据库事务，也不能把顺序闭包示例当作并发 race 证据。
