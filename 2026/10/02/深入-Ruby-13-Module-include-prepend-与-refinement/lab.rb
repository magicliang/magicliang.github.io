# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
module Logging
  def run(events)
    events << :before
    value = super
    events << :after
    value
  end
end
class Work
  def run(events)
    events << :work
    :result
  end
end
class Included < Work
  include Logging
end
class Shadowed < Work
  include Logging
  def run(events)
    events << :own
    :own
  end
end
class Prepended < Work
  prepend Logging
  def run(events)
    events << :own
    super
  end
end
class Wrapper
  def initialize(target) = (@target = target)
  def run(events)
    events << :before
    value = @target.run(events)
    events << :after
    value
  end
end
events = []; check('include inherited wrapper', Included.new.run(events) == :result && events == [:before, :work, :after])
events = []; check('class method shadows included module', Shadowed.new.run(events) == :own && events == [:own])
events = []; check('prepend wraps class', Prepended.new.run(events) == :result && events == [:before, :own, :work, :after])
events = []; check('composition equivalent behavior', Wrapper.new(Work.new).run(events) == :result && events == [:before, :work, :after])
check('prepend ancestor order', Prepended.ancestors.take(3) == [Logging, Prepended, Work])
module LabelRefinement
  refine String do
    def task_label = "task:#{self}"
  end
end
def outside_refinement(value) = value.task_label
module LabelClient
  using LabelRefinement
  def self.label(value) = value.task_label
  def self.outside(value) = outside_refinement(value)
end
check('refinement lexical call site', LabelClient.label('a') == 'task:a')
begin
  LabelClient.outside('a')
  raise 'refinement leaked'
rescue NoMethodError
  puts 'PASS caller does not activate refinement in callee'
end
puts 'PASS lab 13'
