go test -run '^$' -fuzz='^FuzzTaskStateSequence$' -fuzztime=3s -parallel=1 -timeout=90s .
