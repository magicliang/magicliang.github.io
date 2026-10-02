require 'json'
require 'prism'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
source = '[1, 2, 3].map { |number| number * 2 }.sum'
parsed = Prism.parse(source)
raise 'parse failed' unless parsed.success?
invalid = Prism.parse('def broken(')
raise 'invalid source accepted' if invalid.success?
iseq = RubyVM::InstructionSequence.compile(source)
result = iseq.eval
raise 'wrong execution result' unless result == 12
disassembly = iseq.disasm
raise 'block missing' unless disassembly.include?('block in')
raise 'send missing' unless disassembly.include?('mid:map')
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, revision: RUBY_REVISION, prism_version: Prism::VERSION, ast_class: parsed.value.class.name, invalid_errors: invalid.errors.map(&:message), result: result, pass: true)
puts '--- AST ---'
puts parsed.value.inspect
puts '--- ISEQ ---'
puts disassembly
