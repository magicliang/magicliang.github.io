require 'json'
require_relative 'scheduler'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
manual = Fiber.new { |value| next_value = Fiber.yield(value * 2); next_value + 1 }
raise 'yield' unless manual.resume(3) == 6
raise 'resume' unless manual.resume(8) == 9
raise 'termination' if manual.alive?
scheduler = PipeScheduler.new
trace = []
reader, writer = IO.pipe
begin
  Fiber.set_scheduler(scheduler)
  Fiber.schedule do
    trace << 'reader_wait'
    raise 'payload' unless reader.read(1) == 'x'
    trace << 'reader_done'
  ensure
    reader.close
  end
  Fiber.schedule do
    trace << 'writer_start'
    sleep 0.01
    writer.write('x')
    trace << 'writer_done'
  ensure
    writer.close
  end
  Fiber.schedule { sleep 0.005; raise 'controlled failure' }
ensure
  Fiber.set_scheduler(nil)
  reader.close unless reader.closed?
  writer.close unless writer.closed?
end
raise 'ordering' unless trace == %w[reader_wait writer_start writer_done reader_done]
raise 'hook not exercised' unless scheduler.events.any? { |event| event.first == 'io_wait' }
raise 'error missing' unless scheduler.errors.map(&:message) == ['controlled failure']
raise 'close missing' unless scheduler.closed && reader.closed? && writer.closed?
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, scheduler: 'PipeScheduler v1', events: trace, hooks: scheduler.events, errors: scheduler.errors.map(&:message), closed: scheduler.closed, pass: true)
