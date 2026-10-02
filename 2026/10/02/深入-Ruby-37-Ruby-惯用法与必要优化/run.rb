require 'json'
require 'benchmark'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
input = (1..100_000).to_a.freeze
strategies = {
  eager: ->(seen) { input.select { |n| seen[0] += 1; n.even? }.map { |n| n * n }.take(20) },
  lazy: ->(seen) { input.lazy.select { |n| seen[0] += 1; n.even? }.map { |n| n * n }.take(20).force },
  loop: lambda do |seen|
    result = []
    input.each do |n|
      seen[0] += 1
      next unless n.even?
      result << n * n
      break if result.length == 20
    end
    result
  end
}
expected = (1..20).map { |n| (n * 2)**2 }
rows = strategies.transform_values do |work|
  10.times { raise 'warmup mismatch' unless work.call([0]) == expected }
  5.times.map do
    seen = [0]
    GC.start
    before = GC.stat(:total_allocated_objects)
    result = nil
    elapsed = Benchmark.realtime { result = work.call(seen) }
    allocated = GC.stat(:total_allocated_objects) - before
    raise 'contract changed' unless result == expected
    {visited: seen[0], seconds: elapsed, allocations: allocated, rss_kb: IO.popen(['ps', '-o', 'rss=', '-p', Process.pid.to_s], &:read).to_i}
  end
end
raise 'eager traversal' unless rows[:eager].all? { |row| row[:visited] == 100_000 }
raise 'short circuit' unless [:lazy, :loop].all? { |name| rows[name].all? { |row| row[:visited] == 40 } }
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, result: expected, samples: rows, pass: true)
