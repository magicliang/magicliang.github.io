# E07 真实按需读取

独立 VM 固定 containerd、stargz snapshotter/格式、registry、网络与镜像 digest。先校验探针源码包；普通 snapshotter 与远程 snapshotter 各预设冷/热重复轮次、同一 `/ready` 请求、首次大文件读取和只在自建网络里的断网试验。保存每轮下载字节、首请求耗时、错误数、缓存状态及清理；不能仅以 mount/页面构建代替远程读取。目前无 snapshotter/registry，所有数据 `NOT_RUN`。
