# frozen_string_literal: true
raise 'Ruby 3.4 required' unless RUBY_VERSION.start_with?('3.4.')
def check(label, condition)
  raise label unless condition
  puts "PASS #{label}"
end
MutableTask = Struct.new(:id, :tags, keyword_init: true)
TaskValue = Data.define(:id, :tags)
mutable = MutableTask.new(id: 1, tags: []); mutable.id = 2
check('Struct has writer and optional fields', mutable.id == 2 && MutableTask.new.id.nil?)
tags = []; value = TaskValue.new(id: 1, tags: tags)
tags << :ruby
check('Data freeze is shallow', value.frozen? && value.tags == [:ruby] && !value.tags.frozen?)
check('Data has no writer', !value.respond_to?(:id=))
check('with replaces selected field', value.with(id: 2).id == 2 && value.id == 1 && value.with(id: 2).tags.equal?(tags))
check('deconstruct array and hash', value.deconstruct == [1, [:ruby]] && value.deconstruct_keys([:id]) == {id: 1})
matched = case value
          in TaskValue(id: Integer => id, tags:) if tags.include?(:ruby)
            id
          else
            nil
          end
check('class pattern guard and binding', matched == 1)
expected = 1
check('pin uses existing value', (value in {id: ^expected}))
check('hash pattern permits extras', ({id: 1, other: 2} in {id: 1}))
check('hash pattern can reject extras', !({id: 1, other: 2} in {id: 1, **nil}))
begin
  value => {id: 99}
  raise 'rightward mismatch accepted'
rescue NoMatchingPatternError
  puts 'PASS rightward mismatch raises'
end
begin
  TaskValue.new(id: 1)
  raise 'missing field accepted'
rescue ArgumentError
  puts 'PASS Data requires all fields'
end
puts 'PASS lab 15'
