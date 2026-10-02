# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
class Base
  def call(*args, **kwargs, &block) = [args, kwargs, block&.call]
end
class Forward < Base
  def call(*args, **kwargs, &block) = super
end
class Empty < Base
  def call(*args, **kwargs, &block) = super()
end
class Explicit < Base
  def call(*args, **kwargs, &block) = super(:changed, mode: :explicit, &nil)
end
check('bare super forwards args keywords block', Forward.new.call(1, mode: :x) { :block } == [[1], {mode: :x}, :block])
check('super empty still forwards block', Empty.new.call(1, mode: :x) { :block } == [[], {}, :block])
check('explicit super and suppressed block', Explicit.new.call(1) { :block } == [[:changed], {mode: :explicit}, nil])
item = Base.new; sibling = Base.new
def item.call(*args, **kwargs, &block) = [:singleton, super]
check('singleton owner', item.method(:call).owner.equal?(item.singleton_class))
check('sibling owner', sibling.method(:call).owner == Base)
check('singleton super reaches ordinary class', item.call(7) == [:singleton, [[7], {}, nil]])
check('super_method owner', item.method(:call).super_method.owner == Base)
check('singleton chain contains normal class', item.singleton_class.ancestors.take(2) == [item.singleton_class, Base])
puts 'PASS lab 12'
