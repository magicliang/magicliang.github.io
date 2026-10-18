psql -h 127.0.0.1 -p 42797 -U admin -d go38live -Atc 'SELECT id,status,words FROM go_tasks ORDER BY id'
