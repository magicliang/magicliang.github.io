psql -h 127.0.0.1 -p 46715 -U admin -d postgres -Atc "SELECT count(*) FROM pg_database WHERE datname LIKE 'go_task_29_%'"
