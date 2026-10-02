# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
class StaticRules
  def open?(task) = task.fetch(:status) == :open
  def done?(task) = task.fetch(:status) == :done
end
class DynamicRules
  @added = []
  def self.added = @added
  def self.method_added(name) = @added << name
  [:open, :done].each do |status|
    define_method("#{status}?") { |task| task.fetch(:status) == status }
  end
end
task = {status: :open}
check('static and generated behavior agree', [:open?, :done?].all? { |name| StaticRules.new.public_send(name, task) == DynamicRules.new.public_send(name, task) })
check('hook observes generated methods', DynamicRules.added == [:open?, :done?])
check('owner and source location available', DynamicRules.new.method(:open?).owner == DynamicRules && DynamicRules.new.method(:open?).source_location.first == __FILE__)
class RuleProxy
  def initialize(target) = (@target = target)
  private
  def method_missing(name, *args, **kwargs, &block)
    return @target.public_send(name, *args, **kwargs, &block) if [:open?, :done?].include?(name)
    super
  end
  def respond_to_missing?(name, include_private = false)
    [:open?, :done?].include?(name) || super
  end
end
proxy = RuleProxy.new(StaticRules.new)
check('reflection and dynamic call agree', proxy.respond_to?(:open?) && proxy.open?(task) && proxy.method(:open?).call(task))
check('unknown method not advertised', !proxy.respond_to?(:typo?))
begin
  proxy.typo?(task)
  raise 'unknown call swallowed'
rescue NoMethodError => e
  check('unknown name preserved', e.name == :typo?)
end
begin
  proxy.open?({})
  raise 'target failure swallowed'
rescue KeyError
  puts 'PASS target exception propagates'
end
puts 'PASS lab 16'
