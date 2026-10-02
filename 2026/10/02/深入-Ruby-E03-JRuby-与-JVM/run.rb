require 'json'
require 'open3'
require 'rbconfig'
require 'digest'
java = ENV.fetch('JAVA', '/opt/homebrew/opt/openjdk@21/bin/java')
jar = ENV.fetch('JRUBY_JAR', '/private/tmp/ruby-electives-jruby-10.0.5.0.jar')
expected = File.read(File.join(__dir__, 'jruby.sha256')).split.first
raise 'JRuby checksum mismatch' unless Digest::SHA256.file(jar).hexdigest == expected
clean = ENV.keys.grep(/\A(?:BUNDLE|RUBYOPT\z|RUBYLIB\z|GEM_HOME\z|GEM_PATH\z|RUBYGEMS_GEMDEPS\z)/).to_h { |key| [key, nil] }
def invoke(env, *command)
  output, error, status = Open3.capture3(env, *command)
  raise "#{command.inspect}: #{error}" unless status.success?
  puts error unless error.empty?
  JSON.parse(output)
end
common = [invoke(clean, RbConfig.ruby, File.join(__dir__, 'contract.rb')), invoke(clean, java, '-jar', jar, File.join(__dir__, 'contract.rb'))]
raise 'semantic mismatch' unless common[0]['result'] == common[1]['result'] && common.all? { |row| row['pass'] }
interop = invoke(clean, java, '-jar', jar, File.join(__dir__, 'interop.rb'))
raise 'JRuby version' unless interop['jruby'] == '10.0.5.0' && interop['ruby_compatibility'].start_with?('3.4.')
raise 'interop failed' unless interop['pass']
puts JSON.pretty_generate(sha256: expected, cleared_bundle_keys: clean.keys.grep(/\ABUNDLE/), common_contract: common, interop: interop, pass: true)
