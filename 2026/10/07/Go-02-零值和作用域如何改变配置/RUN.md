# 02 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

本目录执行 `sha256sum -c SHA256SUMS` 后解包 `go-language-02.tar.gz`。在解包所得 `go-language/` 中阅读 `VERSIONS.md`、`RUN.md`，按其命令验证旧的统计契约、新的 `--max-words` 边界和 `testdata/` 两个遮蔽对照程序。

包内包含当前完整工程与 00–02 各章原始实验输出。独立解包复跑另记于此目录的 `unpack-*` 文件。任何环境的 Go 版本、数据库或页面结果均不得由这份包的存在自行推断。
