psql -h 127.0.0.1 -p 57745 -U admin -d goe05live -Atc "SELECT id,status,words FROM go_tasks WHERE id='task[0]'"
