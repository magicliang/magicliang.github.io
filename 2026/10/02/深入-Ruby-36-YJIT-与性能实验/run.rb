require 'json'
require 'rbconfig'
require 'open3'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
if ARGV.first == 'sample'
  def calculate(values)
    sum = 0
    values.each { |number| sum += number * 3 + 1 }
    sum
  end
  input = (1..20_000).to_a.freeze
  expected = 3 * 20_000 * 20_001 / 2 + 20_000
  100.times { raise 'warmup result' unless calculate(input) == expected }
  GC.start
  before = GC.stat(:total_allocated_objects)
  start = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  200.times { raise 'result mismatch' unless calculate(input) == expected }
  elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - start
  allocated = GC.stat(:total_allocated_objects) - before
  rss = IO.popen(['ps', '-o', 'rss=', '-p', Process.pid.to_s], &:read).to_i
  puts JSON.generate(ruby: RUBY_DESCRIPTION, enabled: RubyVM::YJIT.enabled?, seconds: elapsed, allocations: allocated, rss_kb: rss, result: expected, stats: RubyVM::YJIT.runtime_stats)
else
  raise 'YJIT API absent' unless defined?(RubyVM::YJIT)
  samples = {interpreter: [], yjit: []}
  5.times do |index|
    modes = index.even? ? samples.keys : samples.keys.reverse
    modes.each do |mode|
      flag = mode == :yjit ? '--yjit' : '--disable-yjit'
      output, error, status = Open3.capture3(RbConfig.ruby, flag, __FILE__, 'sample')
      raise "child failed: #{error}" unless status.success?
      result = JSON.parse(output)
      raise 'YJIT state mismatch' unless result['enabled'] == (mode == :yjit)
      samples[mode] << result
    end
  end
  medians = samples.transform_values { |rows| rows.map { |row| row['seconds'] }.sort[2] }
  puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, workload: '20000 integers, 100 warmup, 200 measured iterations, 5 fresh processes per mode', samples: samples, medians: medians, ratio_interpreter_over_yjit: medians[:interpreter] / medians[:yjit], pass: true)
end
