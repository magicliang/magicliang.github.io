psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 54089 -U admin -d go39live -Atc "SELECT id,status,words,failure_reason FROM go_tasks WHERE id='task[1]'"
