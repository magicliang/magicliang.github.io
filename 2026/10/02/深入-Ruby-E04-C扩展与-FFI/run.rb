require 'json'
require 'tmpdir'
require 'fileutils'
require 'open3'
require 'rbconfig'
raise 'CRuby 3.4 required' unless RUBY_ENGINE == 'ruby' && RUBY_VERSION.start_with?('3.4.')
raise 'POSIX build required' if Gem.win_platform?
clean = ENV.keys.grep(/\A(?:BUNDLE|RUBYOPT\z|RUBYLIB\z|GEM_HOME\z|GEM_PATH\z|RUBYGEMS_GEMDEPS\z)/).to_h { |key| [key, nil] }
commands = []
result = nil
directory = nil
Dir.mktmpdir('ruby-E04-') do |build|
  directory = build
  %w[extconf.rb native_box.c].each { |name| FileUtils.cp(File.join(__dir__, name), build) }
  invoke = lambda do |*command|
    output, error, status = Open3.capture3(clean, *command, chdir: build)
    commands << {command: command, stdout: output, stderr: error, exit: status.exitstatus}
    raise JSON.pretty_generate(commands) unless status.success?
    output
  end
  invoke.call(RbConfig.ruby, 'extconf.rb')
  invoke.call('make')
  library = File.join(build, RbConfig::CONFIG['host_os'].include?('darwin') ? 'bridge.dylib' : 'bridge.so')
  invoke.call(ENV.fetch('CC', 'clang'), '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared', '-pthread', File.join(__dir__, 'bridge.c'), '-o', library)
  result = JSON.parse(invoke.call(RbConfig.ruby, '-I', build, File.join(__dir__, 'probe.rb'), library))
  raise 'probe failed' unless result['pass']
end
raise 'build leaked' if File.exist?(directory)
puts JSON.pretty_generate(build_commands: commands, result: result, temporary_build_removed: true, pass: true)
