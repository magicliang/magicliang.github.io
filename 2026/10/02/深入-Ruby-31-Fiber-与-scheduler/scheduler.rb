# Teaching scheduler v1: single-threaded pipe readiness and timed sleep only.
class PipeScheduler
  attr_reader :events, :errors, :closed

  def initialize
    @waiting = {}
    @events = []
    @errors = []
    @closed = false
  end

  def fiber(&work)
    task = Fiber.new(blocking: false) do
      begin
        work.call
      rescue StandardError => error
        @errors << error
      end
    end
    task.resume
    task
  end

  def io_wait(io, events, timeout = nil)
    @events << ['io_wait', io.fileno, events]
    @waiting[Fiber.current] = [io, events, timeout && now + timeout]
    Fiber.yield
  end

  def kernel_sleep(duration = nil)
    raise ArgumentError, 'finite sleep required' unless duration
    @waiting[Fiber.current] = [nil, 0, now + duration]
    Fiber.yield
    duration
  end

  def block(blocker, timeout = nil)
    raise NotImplementedError, 'indefinite blockers unsupported' unless timeout
    kernel_sleep(timeout)
    false
  end

  def unblock(blocker, fiber)
    @waiting.delete(fiber)
    fiber.resume if fiber.alive?
  end

  def now
    Process.clock_gettime(Process::CLOCK_MONOTONIC)
  end

  def close
    until @waiting.empty?
      entries = @waiting.to_a
      reads = entries.filter_map { |_, (io, mask, _)| io if io && mask & IO::READABLE != 0 }
      writes = entries.filter_map { |_, (io, mask, _)| io if io && mask & IO::WRITABLE != 0 }
      deadline = entries.filter_map { |_, (_, _, time)| time }.min
      delay = deadline && [deadline - now, 0].max
      readable, writable = IO.select(reads, writes, [], delay) || [[], []]
      entries.each do |fiber, (io, mask, time)|
        result = 0
        result |= IO::READABLE if readable.include?(io)
        result |= IO::WRITABLE if writable.include?(io)
        next unless result != 0 || (time && time <= now)
        @waiting.delete(fiber)
        fiber.resume(result) if fiber.alive?
      end
    end
  ensure
    @closed = true
  end
end
