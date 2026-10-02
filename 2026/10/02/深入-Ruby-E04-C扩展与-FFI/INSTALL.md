# E04 隔离原生构建

实测：CRuby3.4.11（完整安装含头文件）、Fiddle1.1.6、Apple clang21、make、arm64 macOS。无额外gem。实验需要POSIX管道、poll和pthread；Windows主动拒绝，Linux代码路径未在本次实测。

```bash
/private/tmp/hexo-ruby-3.4/bin/ruby -rfiddle -e 'p [RUBY_DESCRIPTION, Fiddle::VERSION]'
clang --version
/private/tmp/hexo-ruby-3.4/bin/ruby examples/ruby/labs/E04/run.rb
```

run.rb把extconf.rb/native_box.c复制到Dir.mktmpdir目录，子进程执行mkmf、make，另以clang的C11模式构建bridge，再起独立Ruby进程测试。构建命令与输出进入最终JSON；结果pass=true，temporary_build_removed=true。未改主线Gemfile/lock。可以通过CC指定等价编译器，但改变编译器或平台需要重测。

native_box是教学CRuby扩展，不能拿它作为JRuby兼容测试。GC实验只核对受测缓冲计数与label可达；GVL实验有1200ms有限poll等待，不支持任意异步取消。C线程反例使用原子load/store形成定义明确的丢更新，避免C数据竞争的未定义行为。FFI只接受自产指针和确切长度；禁止外部裸地址、释放后调用或给同一地址配置两个释放所有者。

构建出的.bundle/.so/.dylib以及Makefile只位于临时目录，完成后删除，不提交二进制。
