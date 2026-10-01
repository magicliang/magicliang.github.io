# E01 相同程序、三种边界

独立 Linux VM，先核对 `CHECKSUMS.sha256`、解压探针包，用同一固定 digest 构建可信镜像。仅当硬件虚拟化可用、gVisor/Kata/runc 各安装固定版本并记录宿主/guest 内核后运行。分别请求 `/health`/`/ready`/`/state`，保存每种 runtime 的系统调用错误、容器 ID、PID、内核边界、启动/资源原始数据与清理。缺虚拟化不跑 Kata；云端没有任何运行时/硬件确认，所有比较 `NOT_RUN`。
