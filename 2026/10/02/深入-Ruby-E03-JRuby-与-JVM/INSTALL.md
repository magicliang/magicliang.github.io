# E03 固定环境与运行

实测：CRuby3.4.11、JRuby10.0.5.0（RUBY_VERSION=3.4.5）、OpenJDK21.0.10 Homebrew、arm64 macOS。JRuby10最低Java21；以下路径可按已验证的本机JDK21修改。无额外gem，无主工程依赖变化。

```bash
curl -fL https://repo.maven.apache.org/maven2/org/jruby/jruby-complete/10.0.5.0/jruby-complete-10.0.5.0.jar -o /private/tmp/ruby-electives-jruby-10.0.5.0.jar
curl -fL https://repo.maven.apache.org/maven2/org/jruby/jruby-complete/10.0.5.0/jruby-complete-10.0.5.0.jar.sha256 -o /private/tmp/ruby-electives-jruby-10.0.5.0.sha256
shasum -a 256 /private/tmp/ruby-electives-jruby-10.0.5.0.jar
cat /private/tmp/ruby-electives-jruby-10.0.5.0.sha256
JAVA=/opt/homebrew/opt/openjdk@21/bin/java JRUBY_JAR=/private/tmp/ruby-electives-jruby-10.0.5.0.jar /private/tmp/hexo-ruby-3.4/bin/ruby examples/ruby/labs/E03/run.rb
```

本次远端SHA256与本地均为`df539aab793d21df970c45749f71f2ef39731dcbe7c144427d5910ca7eb9c4b3`。run.rb每次按仓库jruby.sha256校验文件，比较两个独立进程的result并执行JRuby互操作。任何失败返回非零，成功最终pass=true。保留JAR在临时目录，不纳入Git。

本实验未验证整个Taskbook、第三方gem平台包或CPU性能。JAVA必须指向实际可用JDK21；不要用系统默认Java8替代。日志中的JVM线程ID每次会变化，不应锁定某个数字。
