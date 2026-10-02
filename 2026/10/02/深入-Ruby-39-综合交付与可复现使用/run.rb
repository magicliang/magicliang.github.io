require 'json'
require 'tmpdir'
require 'fileutils'
require 'open3'
require 'rbconfig'
require 'rubygems'
raise 'requires Ruby 3.4' unless RUBY_VERSION.start_with?('3.4.')
project = File.expand_path('../..', __dir__)
gem_command = File.join(RbConfig::CONFIG.fetch('bindir'), 'gem')
events = []
Dir.mktmpdir('taskbook-release') do |directory|
  package = File.join(directory, 'taskbook-workshop-0.1.0.gem')
  output, error, status = Open3.capture3(RbConfig.ruby, gem_command, 'build', 'taskbook.gemspec', '--output', package, chdir: project)
  raise "build failed: #{error}" unless status.success?
  events << {step: 'build', output: output}
  spec = Dir.chdir(project) { Gem::Specification.load('taskbook.gemspec') }
  dependencies = spec.runtime_dependencies.dup
  seen = {}
  until dependencies.empty?
    dependency = dependencies.shift
    next if seen[dependency.name]
    installed = Gem::Specification.find_by_name(dependency.name, dependency.requirement)
    seen[dependency.name] = installed.version.to_s
    dependencies.concat(installed.runtime_dependencies)
    next if installed.default_gem?
    cache = installed.cache_file
    raise "missing local gem cache: #{installed.name}" unless File.file?(cache)
    FileUtils.cp(cache, directory)
  end
  gem_home = File.join(directory, 'gems')
  env = {'GEM_HOME' => gem_home, 'GEM_PATH' => gem_home, 'BUNDLE_GEMFILE' => nil, 'RUBYOPT' => nil, 'RUBYLIB' => nil}
  output, error, status = Open3.capture3(env, RbConfig.ruby, gem_command, 'install', package, '--local', '--no-document', chdir: directory)
  raise "install failed: #{error}" unless status.success?
  events << {step: 'install', output: output, dependencies: seen}
  executable = File.join(gem_home, 'bin', 'taskbook')
  input = JSON.generate([
    {id: 1, title: 'keep', priority: 5, tags: ['ruby'], status: 'todo'},
    {id: 2, title: 'drop', priority: 1, tags: [], status: 'done'}
  ])
  csv, error, status = Open3.capture3(env, RbConfig.ruby, executable, 'filter', '--min-priority', '4', '--output-format', 'csv', stdin_data: input, chdir: directory)
  raise "filter failed: #{error}" unless status.success?
  output, error, status = Open3.capture3(env, RbConfig.ruby, executable, 'export', '--format', 'csv', stdin_data: csv, chdir: directory)
  raise "export failed: #{error}" unless status.success?
  raise 'roundtrip mismatch' unless JSON.parse(output).map { |task| task.fetch('id') } == [1]
  events << {step: 'roundtrip', csv: csv, json: JSON.parse(output)}
  _, error, status = Open3.capture3(env, RbConfig.ruby, executable, stdin_data: '{', chdir: directory)
  raise 'invalid input status' unless status.exitstatus == 2 && error.include?('invalid input syntax')
  target = File.join(directory, 'existing.json')
  File.write(target, 'preserve')
  _, error, status = Open3.capture3(env, RbConfig.ruby, executable, '--output', target, stdin_data: input, chdir: directory)
  raise 'overwrite prevention' unless status.exitstatus == 3 && File.read(target) == 'preserve'
  raise 'path leaked' if error.include?(directory)
  events << {step: 'failures', invalid_exit: 2, existing_output_exit: 3, existing_preserved: true}
  output, error, status = Open3.capture3(env, RbConfig.ruby, File.join(__dir__, 'installed_probe.rb'), stdin_data: input, chdir: directory)
  raise "installed probe failed: #{error}" unless status.success?
  events << JSON.parse(output)
end
puts JSON.pretty_generate(ruby: RUBY_DESCRIPTION, events: events, temporary_install_removed: true, pass: true)
