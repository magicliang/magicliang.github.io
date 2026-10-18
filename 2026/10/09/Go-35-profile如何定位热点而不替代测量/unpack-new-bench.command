go test -run "^$" -bench "^BenchmarkTask(AnalyzeContext|HTTPRead)$" -benchmem -benchtime=200ms -count=5 .
