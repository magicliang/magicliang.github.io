require 'json'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
raise 'Ractor unavailable' unless defined?(Ractor)
shallow = ['mutable'.dup].freeze
raise 'shallow freeze unexpectedly shareable' if Ractor.shareable?(shallow)
deep = Ractor.make_shareable(['value'.dup])
raise 'deep shareability' unless Ractor.shareable?(deep) && deep.first.frozen?
copy = ['original'.dup]
receiver = Ractor.new { value = Ractor.receive; value.first.replace('changed'); value }
receiver.send(copy)
received = receiver.take
raise 'copy isolation' unless received == ['changed'] && copy == ['original']
moved = ['moved'.dup]
receiver = Ractor.new { Ractor.receive.first.upcase }
receiver.send(moved, move: true)
error = begin
  moved.length
  nil
rescue Ractor::MovedError => exception
  exception.class.name
end
raise 'move access not rejected' unless error == 'Ractor::MovedError'
raise 'move result' unless receiver.take == 'MOVED'
shared_id = Ractor.new(deep) { |value| value.object_id }.take
raise 'shared identity' unless shared_id == deep.object_id
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, shallow_shareable: false, deep_shareable: true, original: copy, received: received, moved_error: error, shared_identity: true, pass: true)
