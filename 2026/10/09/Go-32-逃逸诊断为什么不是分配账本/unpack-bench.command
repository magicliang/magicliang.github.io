go test -run "^$" -bench "^BenchmarkTask(CountWords|FieldsReference)$" -benchmem -benchtime=200ms -count=5 ./stats
