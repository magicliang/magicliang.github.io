# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
outer = :captured
check('block captures local and preserves self', [1].map { [outer, self] }.first == [:captured, self])
klass = Class.new do
  define_method(:captured) { outer }
  def isolated
    outer
  end
end
check('define_method captures local', klass.new.captured == :captured)
begin
  klass.new.isolated
  raise 'def unexpectedly captured local'
rescue NameError
  puts 'PASS def has separate local scope'
end
module ScopeLab
  TOKEN = :outer
  module Nested
    NESTING = Module.nesting
    VALUE = TOKEN
    RECEIVER = self
  end
end
module ScopeLab::Flat
  NESTING = Module.nesting
  begin
    TOKEN
    raise 'flat definition unexpectedly sees outer'
  rescue NameError
    MISSING = true
  end
end
check('nested lexical constants', ScopeLab::Nested::VALUE == :outer)
check('nested Module.nesting', ScopeLab::Nested::NESTING == [ScopeLab::Nested, ScopeLab])
check('class body self', ScopeLab::Nested::RECEIVER.equal?(ScopeLab::Nested))
check('qualified reopening omits outer nesting', ScopeLab::Flat::NESTING == [ScopeLab::Flat] && ScopeLab::Flat::MISSING)
class ScopeParent
  TOKEN = :parent
  def token = TOKEN
end
class ScopeChild < ScopeParent
  TOKEN = :child
  def own_token = TOKEN
end
check('inherited method retains definition context', ScopeChild.new.token == :parent && ScopeChild.new.own_token == :child)
puts 'PASS lab 09'
