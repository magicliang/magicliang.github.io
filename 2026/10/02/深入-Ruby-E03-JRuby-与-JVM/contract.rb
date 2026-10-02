raise 'inherited Bundler environment' unless ENV.keys.grep(/\ABUNDLE/).empty?
require 'json'
require 'thread'
def select_tasks(tasks, status:, limit:)
  raise ArgumentError, 'limit' unless limit.is_a?(Integer) && limit.positive?
  tasks.select { |task| task.fetch(:status) == status }.first(limit).map { |task| task.fetch(:title) }
end
tasks = [{title: '写作', status: :todo}, {title: '校验', status: :done}]
raise 'keywords/result' unless select_tasks(tasks, status: :todo, limit: 1) == ['写作']
errors = []
begin
  select_tasks(tasks, {status: :todo, limit: 1})
rescue ArgumentError
  errors << 'positional_hash_rejected'
end
begin
  select_tasks(tasks, status: :todo, limit: 0)
rescue ArgumentError
  errors << 'invalid_limit_rejected'
ensure
  errors << 'ensure'
end
raise 'errors' unless errors == %w[positional_hash_rejected invalid_limit_rejected ensure]
original = ['title']
copy = original.dup
copy[0] << '!'
raise 'shallow copy' unless original == ['title!']
ready, release = Queue.new, Queue.new
counter = 0
threads = 2.times.map do
  Thread.new { old = counter; ready << true; release.pop; counter = old + 1 }
end
2.times { ready.pop }; 2.times { release << true }; threads.each(&:value)
raise 'controlled race' unless counter == 1
mutex = Mutex.new
counter = 0
2.times.map { Thread.new { 1_000.times { mutex.synchronize { counter += 1 } } } }.each(&:value)
raise 'mutex' unless counter == 2_000
puts JSON.generate(engine: RUBY_ENGINE, ruby: RUBY_VERSION, result: {titles: ['写作'], errors: errors, shared_nested: original, race: 1, mutex: counter}, pass: true)
