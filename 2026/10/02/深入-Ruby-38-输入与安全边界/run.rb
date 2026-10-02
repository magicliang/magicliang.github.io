require 'json'
require 'tmpdir'
require 'open3'
require 'rbconfig'
require 'psych'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
def read_document(root, name)
  raise ArgumentError, 'invalid document' unless name.match?(/\A[a-z0-9_-]+\.json\z/)
  path = File.join(root, name)
  raise ArgumentError, 'invalid document' if File.symlink?(path)
  JSON.parse(File.read(path))
rescue Errno::ENOENT, JSON::ParserError
  raise ArgumentError, 'invalid document'
end
checks = []
Dir.mktmpdir('ruby-boundary') do |root|
  File.write(File.join(root, 'tasks.json'), '[{"title":"demo"}]')
  raise 'valid document' unless read_document(root, 'tasks.json') == [{'title' => 'demo'}]
  ['../private.json', '/etc/passwd', 'missing.json'].each do |name|
    begin
      read_document(root, name)
      raise 'accepted hostile name'
    rescue ArgumentError => error
      raise 'detail leakage' unless error.message == 'invalid document'
      checks << name
    end
  end
  File.symlink(File.join(root, 'tasks.json'), File.join(root, 'link.json'))
  begin
    read_document(root, 'link.json')
    raise 'accepted symbolic link'
  rescue ArgumentError
    checks << 'symlink'
  end
  hostile = '; touch NEVER_CREATED'
  output, _, status = Open3.capture3(RbConfig.ruby, '-e', 'print ARGV.fetch(0)', hostile, chdir: root)
  raise 'argument not literal' unless status.success? && output == hostile
  raise 'shell expansion' if File.exist?(File.join(root, 'NEVER_CREATED'))
  checks << 'literal_argument'
end
commands = {'count' => ->(items) { items.length }}.freeze
raise 'dispatch' unless commands.fetch('count').call([1, 2]) == 2
begin
  commands.fetch('instance_eval')
  raise 'unauthorized dispatch'
rescue KeyError
  checks << 'dispatch_denied'
end
begin
  Psych.safe_load("--- !ruby/object:Object {}\n", permitted_classes: [], permitted_symbols: [], aliases: false)
  raise 'object deserialized'
rescue Psych::DisallowedClass
  checks << 'unsafe_yaml_denied'
end
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, psych: Psych::VERSION, checks: checks, limitation: 'filename allowlist and symlink check assume a private directory; not a race-safe hostile-filesystem sandbox', pass: true)
