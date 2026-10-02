require 'taskbook/http'
require 'socket'
require 'net/http'
require 'json'
require 'stringio'
payload = STDIN.read
location = Gem.loaded_specs.fetch('taskbook-workshop').full_gem_path
installed_root = File.realpath(ENV.fetch('GEM_HOME')) + File::SEPARATOR
raise "loaded outside isolated GEM_HOME: #{location}" unless File.realpath(location).start_with?(installed_root)
server = TCPServer.new('127.0.0.1', 0)
port = server.addr[1]
closed = 0
worker = Thread.new do
  3.times do
    connection = server.accept
    body = nil
    begin
      request = connection.gets.split
      headers = {}
      while (line = connection.gets) && line != "\r\n"
        key, value = line.split(':', 2)
        headers[key.downcase] = value.strip
      end
      length = Integer(headers.fetch('content-length', '0'))
      input = StringIO.new(connection.read(length))
      code, response_headers, body = Taskbook::HTTPApp.new.call('REQUEST_METHOD' => request[0], 'PATH_INFO' => request[1], 'CONTENT_TYPE' => headers['content-type'], 'rack.input' => input)
      connection.write("HTTP/1.1 #{code} Response\r\n")
      response_headers.each { |key, value| connection.write("#{key}: #{value}\r\n") }
      connection.write("Connection: close\r\n\r\n")
      body.each { |chunk| connection.write(chunk) }
    ensure
      body.close if body.respond_to?(:close)
      input&.close
      connection.close
      closed += 1
    end
  end
end
begin
  results = [['/tasks', payload], ['/tasks', '{'], ['/missing', payload]].map do |path, data|
    http = Net::HTTP.new('127.0.0.1', port, nil)
    http.open_timeout = http.read_timeout = http.write_timeout = 2
    http.max_retries = 0
    response = http.start { |session| session.post(path, data, 'Content-Type' => 'application/json') }
    {status: response.code.to_i, body: JSON.parse(response.body)}
  end
  worker.value
  raise 'HTTP statuses' unless results.map { |result| result[:status] } == [200, 400, 404]
  raise 'HTTP result' unless results.first[:body].fetch('total') == 2
  raise 'connection leak' unless closed == 3
ensure
  server.close
  worker.kill if worker.alive?
  worker.join
end
puts JSON.generate(step: 'installed_http', source: location, responses: results, accepted_connections_closed: closed, listener_closed: server.closed?)
