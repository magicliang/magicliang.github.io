# E03 内核事件的 Pod 身份

独立 VM 中固定 BPF loader 程序、内核、kubelet、CRI 版本并审计探针源码；校验随文 probe-app 包。在自建 Pod 打开自己的状态文件，BPF 事件记录时间、PID/TGID、cgroup ID、namespace inode，用户态同时解析 Pod UID、容器 ID 和进程启动时间。删除/重建同名 Pod 后重新关联，清理 BPF 程序及自建 namespace；不能只用事后 `/proc/<pid>` 代表历史事件。当前无 BPF 探针/kind，`NOT_RUN`。
