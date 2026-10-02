raise 'inherited Bundler environment' unless ENV.keys.grep(/\ABUNDLE/).empty?
require 'json'
require 'java'
java_import java.util.concurrent.CountDownLatch
java_import java.util.concurrent.TimeUnit
java_import java.util.concurrent.atomic.AtomicInteger
ready, start = CountDownLatch.new(2), CountDownLatch.new(1)
ids, events = Queue.new, Queue.new
counter = AtomicInteger.new(0)
threads = 2.times.map do |index|
  Thread.new do
    java_thread = java.lang.Thread.currentThread
    ids << java_thread.threadId
    events << [index, 'ready']
    ready.countDown
    raise 'start timeout' unless start.await(5, TimeUnit::SECONDS)
    1_000.times { counter.incrementAndGet }
    events << [index, 'done']
  end
end
begin
  raise 'ready timeout' unless ready.await(5, TimeUnit::SECONDS)
  raise 'workers not alive' unless threads.all?(&:alive?)
  start.countDown
  threads.each { |thread| raise 'join timeout' unless thread.join(5); thread.value }
ensure
  start.countDown
  threads.each { |thread| thread.kill if thread.alive?; thread.join }
end
thread_ids = 2.times.map { ids.pop }
raise 'same Java thread' unless thread_ids.uniq.size == 2
raise 'atomic result' unless counter.get == 2_000
values = java.util.ArrayList.new
values.add('写作'); values.add('校验')
raise 'java collection' unless values.to_a == ['写作', '校验']
amount = java.math.BigDecimal.new('0.1').add(java.math.BigDecimal.new('0.2')).toPlainString
raise 'decimal' unless amount == '0.3'
error_class = nil
begin
  java.lang.Integer.parseInt('not-an-integer')
rescue Java::JavaLang::NumberFormatException => error
  error_class = error.java_class.name
end
raise 'Java exception' unless error_class == 'java.lang.NumberFormatException'
trace = []; trace << events.pop until events.empty?
raise 'barrier event order' unless trace.first(2).all? { |event| event[1] == 'ready' } && trace.last(2).all? { |event| event[1] == 'done' }
puts JSON.pretty_generate(jruby: JRUBY_VERSION, ruby_compatibility: RUBY_VERSION, java: java.lang.System.getProperty('java.runtime.version'), vm: java.lang.System.getProperty('java.vm.name'), thread_ids: thread_ids, events: trace, atomic: counter.get, decimal: amount, java_exception: error_class, threads_closed: threads.none?(&:alive?), pass: true)
