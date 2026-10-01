# 39 CPU weight 可证伪实验

原始来源：Linux kernel cgroup v2 CPU controller 文档；在专用 VM 固定内核、cgroup v2 版本、CPU 拓扑/频率、cpuset、父组及委派、相同 probe 源码 SHA。先在独立运行设计表中预注册 100:200 weight 两组竞争、只有一组运行、对调 weight/顺序三种条件。每组至少十次，保留每轮 `cpu.stat` 前后、工作量、总时长、失败率及异常负载；不要预写结果数字。

```sh
python3 bounded_load.py --seconds 2 --memory-mib 0
cat "$OWN_GROUP_A/cpu.weight" "$OWN_GROUP_A/cpu.stat"
cat "$OWN_GROUP_B/cpu.weight" "$OWN_GROUP_B/cpu.stat"
```

只在自己被委派的可写 cgroup 创建子组、限负载最长两秒，结束时确认子组无进程并删除。当前 cgroup v1 只读，基线/十次重复/反例/恢复结果全 `NOT_RUN`；正文不能以预测替代研究结论。
