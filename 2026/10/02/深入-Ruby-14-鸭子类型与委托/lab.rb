# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
class MemorySource
  include Enumerable
  def initialize(rows) = (@rows = rows)
  def each
    return enum_for(__method__) unless block_given?
    @rows.each { |row| yield row }
    self
  end
end
class GeneratedSource
  include Enumerable
  def each
    return enum_for(__method__) unless block_given?
    3.times { |i| yield({id: i + 1}) }
    self
  end
end
def ids(source)
  result = []
  source.each { |row| result << row.fetch(:id) }
  result
end
check('independent sources share each contract', ids(MemorySource.new([{id: 1}, {id: 2}, {id: 3}])) == ids(GeneratedSource.new))
check('each returns enumerator without block', GeneratedSource.new.each.take(2) == [{id: 1}, {id: 2}])
class ExplicitArray
  def to_a = [1, 2]
end
class ImplicitArray
  def to_ary = [1, 2]
end
check('Array conversion can use to_a', Array(ExplicitArray.new) == [1, 2])
check('Array plus uses to_ary', [0] + ImplicitArray.new == [0, 1, 2])
begin
  [0] + ExplicitArray.new
  raise 'to_a unexpectedly implicit'
rescue TypeError
  puts 'PASS explicit conversion does not satisfy implicit protocol'
end
class Delegate
  def initialize(target) = (@target = target)
  def each(&block) = @target.each(&block)
end
check('explicit delegation preserves block', ids(Delegate.new(GeneratedSource.new)) == [1, 2, 3])
bad = Object.new
def bad.each = :not_iteration
check('respond_to only advertises name', bad.respond_to?(:each) && ids(bad).empty?)
begin
  ids(MemorySource.new([{}]))
  raise 'invalid row accepted'
rescue KeyError
  puts 'PASS invalid element propagates failure'
end
puts 'PASS lab 14'
