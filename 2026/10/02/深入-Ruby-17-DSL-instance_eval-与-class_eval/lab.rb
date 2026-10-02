# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
class Rules
  attr_reader :minimum
  def priority_at_least(value)
    raise ArgumentError, 'priority' unless value.is_a?(Integer) && (1..3).cover?(value)
    @minimum = value
    self
  end
  def match?(task) = task.fetch(:priority) >= minimum
  def self.build(&block)
    rules = new
    rules.instance_eval(&block)
    raise ArgumentError, 'missing priority' unless rules.minimum
    rules
  end
end
threshold = 2
plain = Rules.new.priority_at_least(threshold)
dsl = Rules.build { priority_at_least(threshold) }
rows = [{priority: 1}, {priority: 2}, {priority: 3}]
check('ordinary API and DSL agree', rows.select { plain.match?(it) } == rows.select { dsl.match?(it) })
target = Object.new
outer_self = self
check('instance_eval changes self and keeps locals', target.instance_eval { [self, threshold, outer_self] } == [target, 2, self])
check('instance_exec passes explicit values', target.instance_exec(3) { |x| x + threshold } == 5)
module DefinitionContext
  TOKEN = :lexical
  def self.install(klass)
    klass.class_eval { define_method(:token) { TOKEN } }
  end
end
class EvalTarget
  TOKEN = :target
end
DefinitionContext.install(EvalTarget)
check('class_eval block keeps constant definition context', EvalTarget.new.token == :lexical)
EvalTarget.class_eval('def string_token; TOKEN; end', __FILE__, __LINE__)
check('class_eval string uses target constant context', EvalTarget.new.string_token == :target)
begin
  Rules.build { priority_at_least(9) }
  raise 'invalid DSL accepted'
rescue ArgumentError
  puts 'PASS DSL validates ordinary API boundary'
end
begin
  Rules.build {}
  raise 'incomplete DSL accepted'
rescue ArgumentError
  puts 'PASS incomplete DSL rejected'
end
puts 'PASS lab 17'
