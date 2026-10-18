# 14 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先执行 `sha256sum -c SHA256SUMS`，解包 `go-language-14.tar.gz`，进入 `go-language/` 查 `VERSIONS.md` 与 `RUN.md`。包内含 14 章完整累计工程、本章真实 Go 实验与早期章节除 HTTP 下载二进制外的 Go 命令和文本结果。前章的原始 HTTP 二进制仍在对应文章素材目录。

`unpack-*` 保存本机独立解包后的测试、构建、64 KiB 边界、坏 JSON、stdin/file JSON、旧 CLI 与排序列表的实际运行及退出码。文件归本工程关闭；stdin/stdout 由调用者管理。输出 Writer 已接受的字节不能回滚，发现短写并返回 2 不能被当成“完全没写出”。
