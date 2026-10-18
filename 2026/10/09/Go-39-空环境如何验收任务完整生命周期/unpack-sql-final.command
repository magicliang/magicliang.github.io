psql -h 127.0.0.1 -p 54089 -U admin -d go39live -Atc 'SELECT id,status,cancel_requested,words,failure_reason FROM go_tasks ORDER BY id'
