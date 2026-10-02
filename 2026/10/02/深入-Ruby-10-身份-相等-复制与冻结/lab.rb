# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
a = ['ruby']; b = ['ruby']
check('identity differs from value', a == b && !a.equal?(b))
check('numeric == differs from eql?', 1 == 1.0 && !1.eql?(1.0))
copy = a.dup
check('dup is shallow', !copy.equal?(a) && copy.first.equal?(a.first))
a.freeze
box = [+'ruby'].freeze
box.first << '!'
check('freeze is shallow', box == ['ruby!'])
begin
  box << 'x'
  raise 'frozen append accepted'
rescue FrozenError
  puts 'PASS outer mutation rejected'
end
object = Object.new
def object.label = :singleton
object.freeze
check('clone preserves singleton and frozen state', object.clone.label == :singleton && object.clone.frozen?)
check('dup drops singleton and frozen state', !object.dup.respond_to?(:label) && !object.dup.frozen?)
check('clone can unfreeze copy', !object.clone(freeze: false).frozen?)
class TaskKey
  attr_reader :id
  def initialize(id) = (@id = id)
  def eql?(other) = other.instance_of?(self.class) && id.eql?(other.id)
  alias == eql?
  def hash = [self.class, id].hash
end
k1 = TaskKey.new(7); k2 = TaskKey.new(7)
check('hash key contract', k1.eql?(k2) && k1.hash == k2.hash && {k1 => :task}[k2] == :task)
key = [1]; index = {key => :task}; key << 2
index.rehash
check('rehash rebuilds mutated key index', index[[1, 2]] == :task)
puts 'PASS lab 10'
