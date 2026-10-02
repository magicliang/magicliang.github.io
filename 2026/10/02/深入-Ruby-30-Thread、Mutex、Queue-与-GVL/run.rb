require 'json'
require 'benchmark'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
ready = Queue.new
release = Queue.new
events = Queue.new
counter = 0
threads = 2.times.map do |id|
  Thread.new do
    old = counter
    events << [id, 'read', old]
    ready << true
    release.pop
    counter = old + 1
    events << [id, 'write', counter]
  end
end
2.times { ready.pop }
2.times { release << true }
threads.each(&:value)
raise 'race not constructed' unless counter == 1
unsafe = counter
counter = 0
mutex = Mutex.new
2.times.map { Thread.new { 1_000.times { mutex.synchronize { counter += 1 } } } }.each(&:value)
raise 'lost synchronized update' unless counter == 2_000
work = -> { (1..300_000).reduce(0) { |sum, n| (sum + n * n) % 1_000_003 } }
cpu = 5.times.map do
  serial = Benchmark.realtime { 2.times { work.call } }
  parallel = Benchmark.realtime { 2.times.map { Thread.new { work.call } }.each(&:value) }
  {serial: serial, threads: parallel}
end
readers = []
writers = []
io_ready = Queue.new
io_events = Queue.new
workers = 2.times.map do |id|
  reader, writer = IO.pipe
  readers << reader
  writers << writer
  Thread.new { io_events << [id, 'waiting']; io_ready << true; io_events << [id, 'read', reader.read(1)] }
end
2.times { io_ready.pop }
writers.each { |writer| writer.write('x'); writer.close }
workers.each(&:value)
readers.each(&:close)
trace = []
trace << events.pop until events.empty?
io_trace = []
io_trace << io_events.pop until io_events.empty?
raise 'I/O workers did not both finish' unless io_trace.count { |event| event[1] == 'read' } == 2
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, race: unsafe, synchronized: counter, events: trace, cpu_samples: cpu, io_events: io_trace, pass: true)
