# 07 素材包复跑

当前源码校验使用 `sha256sum -c CURRENT-SHA256SUMS`；包内 `evidence/*/source-sha.stdout` 是历史写作证据。

先在本目录运行 `sha256sum -c SHA256SUMS`，解包 `go-language-07.tar.gz`，进入包内 `go-language/` 阅读 `VERSIONS.md`、`RUN.md`。归档包含唯一累计工程与 `evidence/00/` 至 `evidence/07/` 的 Go 原始运行命令、双流与退出码。为了不把早期包的 HTTP 下载二进制按章节递归复制，归档中省去前 00–06 章的 `http-archive.body`；其原始下载正文与原章素材包仍保存在仓库。07 本章 Go 命令与证据完整保留。

`testdata/nil-map-write.go` 独立编译后会 panic，本机真实退出码记录于 07 原始日志；不要把 `go run` 外层的状态当成短程序的退出码。`unpack-*` 是实际解包复跑的文件；Hexo 页面与本地 HTTP 检查另行留证。此索引没有跨进程持久化功能。
