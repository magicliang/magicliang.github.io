go test -run '^$' -fuzz='^FuzzCountWordsMatchesFields$' -fuzztime=3s -parallel=1 -timeout=90s ./stats
