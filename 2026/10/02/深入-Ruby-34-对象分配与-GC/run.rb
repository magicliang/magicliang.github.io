require 'json'
require 'objspace'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
def snapshot(label, cache)
  GC.start(full_mark: true, immediate_sweep: true)
  {label: label, gc: GC.stat.slice(:total_allocated_objects, :total_freed_objects, :heap_live_slots, :count), cache_entries: cache.size, cache_bytes: cache.sum { |value| ObjectSpace.memsize_of(value) }, rss_kb: IO.popen(['ps', '-o', 'rss=', '-p', Process.pid.to_s], &:read).to_i}
end
cache = []
rows = [snapshot('baseline', cache)]
3.times do |round|
  5_000.times { |index| cache << "#{round}:#{index}:#{'x' * 100}" }
  rows << snapshot("retained_#{round + 1}", cache)
end
raise 'retention count' unless cache.length == 15_000
raise 'allocation counter' unless rows.last[:gc][:total_allocated_objects] > rows.first[:gc][:total_allocated_objects]
retained = rows.last[:cache_bytes]
cache.clear
rows << snapshot('cleared', cache)
raise 'reference release' unless rows.last[:cache_entries].zero? && rows.last[:cache_bytes].zero? && retained > 0
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, gc_config: GC.config, samples: rows, pass: true)
