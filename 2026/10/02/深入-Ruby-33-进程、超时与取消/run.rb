require 'json'
require 'timeout'
require 'rbconfig'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
events = []
begin
  Timeout.timeout(0.02) do
    begin
      sleep 10
    ensure
      events << 'timeout_ensure'
    end
  end
rescue Timeout::Error
  events << 'timeout_error'
end
raise 'ensure missing' unless events == %w[timeout_ensure timeout_error]
reader, writer = IO.pipe
pid = nil
status = nil
begin
  script = "STDOUT.sync=true; trap('TERM') { exit 23 }; puts 'ready'; sleep 60"
  pid = Process.spawn(RbConfig.ruby, '-e', script, out: writer)
  writer.close
  raise 'child not ready' unless IO.select([reader], nil, nil, 5)
  raise 'handshake' unless reader.gets == "ready\n"
  events << 'child_ready'
  start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  raise 'unexpected data' if IO.select([reader], nil, nil, 0.02)
  events << 'deadline_expired'
  Process.kill('TERM', pid)
  events << 'term_sent'
  deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + 2
  until (waited = Process.wait2(pid, Process::WNOHANG))
    if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
      Process.kill('KILL', pid)
      events << 'kill_sent'
      waited = Process.wait2(pid)
      break
    end
    sleep 0.001
  end
  _, status = waited
  pid = nil
  events << 'reaped'
  raise 'wrong child status' unless status.exited? && status.exitstatus == 23
ensure
  if pid
    Process.kill('KILL', pid) rescue Errno::ESRCH
    Process.wait(pid) rescue Errno::ECHILD
  end
  reader.close unless reader.closed?
  writer.close unless writer.closed?
end
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, timeout_version: Gem.loaded_specs['timeout']&.version.to_s, timeout_source: Timeout.method(:timeout).source_location, events: events, exitstatus: status.exitstatus, pipes_closed: reader.closed? && writer.closed?, pass: true)
