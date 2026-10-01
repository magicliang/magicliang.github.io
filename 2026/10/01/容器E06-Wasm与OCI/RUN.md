# E06 选定 WASI 能力再执行

独立 VM 固定 Wasm runtime、WASI 版本、模块工具链和 OCI 集成版本，先校验本目录源码包。编写与 probe-app `/health` 可对照的最小模块并保留源文件、编译命令/产物 SHA，验证所选实现确实提供需要的网络/文件能力；用支持该制品的 runtime 运行一次，再让传统 runc 运行相同模块作为不兼容对照并清理。当前无 Wasm toolchain/runtime，两个场景均 `NOT_RUN`；该源码包只提供 Linux 程序，不是假装已经写好 Wasm 模块。
