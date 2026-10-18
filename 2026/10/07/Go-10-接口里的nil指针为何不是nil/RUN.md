# 10 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先在本目录执行 `sha256sum -c SHA256SUMS`，解包 `go-language-10.tar.gz`，进入 `go-language/` 阅读 `VERSIONS.md` 和 `RUN.md`；归档内包含截至 10 的完整累计工程与 10 当章完整 Go 运行证据。较早章节的 HTTP 下载二进制未递归复制，原版留在各章素材目录，历史 Go 命令和文本结果仍随包提供。

`testdata/typed-nil.go` 的 bad 分支是预期出现的逻辑反例，短程序本身正常退出 0；请核对两条输出的三个布尔位。`unpack-*` 是本章真实独立解包后校验、构建、测试、正反查询与独立短程序的原始记录。
