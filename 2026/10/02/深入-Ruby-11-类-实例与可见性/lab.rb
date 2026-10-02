# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
def rejects(error)
  yield
  raise "expected #{error}"
rescue error
  puts "PASS expected #{error}"
end
class Task
  attr_reader :title, :status
  def initialize(title:, priority:)
    raise ArgumentError, 'title' unless title.is_a?(String) && !title.empty?
    raise ArgumentError, 'priority' unless priority.is_a?(Integer) && (1..3).cover?(priority)
    @title = title.dup.freeze
    @priority = priority
    @status = :open
  end
  def complete!
    self.require_open!
    @status = :done
    self
  end
  def higher_than?(other) = priority > other.priority
  def aliased_private
    receiver = self
    receiver.require_open!
  end
  protected
  attr_reader :priority
  private
  def require_open!
    raise ArgumentError, 'already done' unless status == :open
  end
end
title = +'write'; task = Task.new(title: title, priority: 3); title << '!'
check('constructor owns title snapshot', task.title == 'write')
check('protected peer comparison', task.higher_than?(Task.new(title: 'read', priority: 1)))
rejects(NoMethodError) { task.priority }
rejects(NoMethodError) { task.aliased_private }
check('literal self private call and transition', task.complete!.equal?(task) && task.status == :done)
rejects(ArgumentError) { task.complete! }
check('failed transition preserves state', task.status == :done)
rejects(ArgumentError) { Task.new(title: '', priority: 2) }
rejects(ArgumentError) { Task.new(title: 'x', priority: 9) }
check('initialize remains private', Task.private_instance_methods.include?(:initialize))
puts 'PASS lab 11'
