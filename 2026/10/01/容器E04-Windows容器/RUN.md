# E04 Windows 组合前提

需要独立 Windows VM、明确 Windows Server 版本与匹配的 Windows 基础镜像 digest、Windows 容器引擎版本。`probe-bundle.tar.gz` 仅提供 Linux 侧功能定义，需要在 VM 中实现同功能 Windows 可执行探针；记录两种隔离模式的实际容器/进程、请求和兼容错误。宿主 Linux `uname` 或改 index 的 os 字段都不能替代 Windows 实测。本云端无 Windows VM，编译/执行/兼容均 `NOT_RUN`。
