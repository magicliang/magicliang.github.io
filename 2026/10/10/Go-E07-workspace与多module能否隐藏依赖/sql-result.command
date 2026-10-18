psql 'host=127.0.0.1 port=45891 user=admin dbname=postgres sslmode=disable' -Atc "SELECT id,status,words FROM go_tasks WHERE id='task[1]'"
