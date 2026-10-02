raise 'inherited Bundler environment' unless ENV.keys.grep(/\ABUNDLE/).empty?
require 'json'
require 'fiddle'
require 'native_box'
def expect_error(klass)
  begin
    yield
  rescue klass
    return klass.name
  end
  raise "expected #{klass}"
end
errors = []
errors << expect_error(TypeError) { NativeBox.new('8', 'label') }
errors << expect_error(ArgumentError) { NativeBox.new(0, 'label') }
errors << expect_error(TypeError) { NativeBox.new(8, nil) }
box = NativeBox.new(8, String.new('retained-by-C'))
GC.start(full_mark: true, immediate_sweep: true)
GC.compact
raise 'mark/compaction' unless box.label == 'retained-by-C' && box.label.frozen?
raise 'owned data' unless box.read == 'A' * 8
raise 'explicit close' unless box.close && !box.close
errors << expect_error(IOError) { box.read }
raise 'explicit leak' unless NativeBox.live_buffers == 0
def abandon_boxes
  50.times { NativeBox.new(32, String.new('gc-owned')) }
end
abandon_boxes
before_gc = NativeBox.live_buffers
3.times { GC.start(full_mark: true, immediate_sweep: true) }
raise 'GC fallback leak' unless before_gc > 0 && NativeBox.live_buffers == 0
wait_results = [false, true].map do |unlock|
  ready_r, ready_w = IO.pipe
  input_r, input_w = IO.pipe
  worker = nil
  begin
    worker = Thread.new { NativeBox.wait_for_token(ready_w.fileno, input_r.fileno, unlock) }
    raise 'ready timeout' unless IO.select([ready_r], nil, nil, 5)
    raise 'ready token' unless ready_r.read(1) == 'r'
    active = NativeBox.waiting?
    input_w.write('x')
    raise 'join timeout' unless worker.join(5)
    result = worker.value
    raise 'GVL behavior' unless result == unlock
    raise 'released region not active' if unlock && !active
    {release_gvl: unlock, native_active_when_ruby_responded: active, native_received: result}
  ensure
    input_w.close unless input_w.closed?
    worker.join if worker
    [ready_r, ready_w, input_r].each { |io| io.close unless io.closed? }
  end
end
handle = Fiddle.dlopen(ARGV.fetch(0))
function = ->(name, arguments, result) { Fiddle::Function.new(handle[name], arguments, result, need_gvl: false) }
make = function.call('owned_new', [Fiddle::TYPE_INT], Fiddle::TYPE_VOIDP)
free = function.call('owned_free', [Fiddle::TYPE_VOIDP], Fiddle::TYPE_VOID)
live = function.call('owned_live', [], Fiddle::TYPE_INT)
checksum = function.call('checksum', [Fiddle::TYPE_VOIDP, Fiddle::TYPE_INT], Fiddle::TYPE_INT)
counter = function.call('native_counter', [Fiddle::TYPE_INT], Fiddle::TYPE_INT)
raise 'FFI invalid size' unless make.call(0).null?
raise 'FFI error sentinel' unless checksum.call(0, 8) == -1
raw = make.call(8)
raise 'FFI allocation' if raw.null?
owner = Fiddle::Pointer.new(raw.to_i, 8, free)
begin
  raise 'FFI checksum' unless checksum.call(owner, 8) == 520 && live.call == 1
ensure
  owner.call_free
end
owner.call_free
raise 'FFI release' unless owner.freed? && live.call == 0
lost, safe = counter.call(0), counter.call(1)
raise 'native atomicity' unless lost == 1 && safe == 2000
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, fiddle: Fiddle::VERSION, errors: errors, retained_label: box.label, gc_buffers_before: before_gc, gc_buffers_after: NativeBox.live_buffers, gvl: wait_results, ffi_checksum: 520, ffi_freed: owner.freed?, ffi_live: live.call, native_lost: lost, native_atomic: safe, pass: true)
