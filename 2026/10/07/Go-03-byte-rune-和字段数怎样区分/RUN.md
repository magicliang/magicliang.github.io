# 03 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先在素材目录执行 `sha256sum -c SHA256SUMS`，再解包 `go-language-03.tar.gz`。进入所得 `go-language/` 阅读 `VERSIONS.md` 和 `RUN.md`，在冻结工具链上重跑统计包与 CLI、以及空串的不同输入契约。

包内是截至 03 的同一个工程及 00–03 的原始 Go 实验证据；这里另保存一次真实独立解包后的 `unpack-*` 命令、双流与退出码。其他平台、HTTP 服务与 SQL 尚未运行。
