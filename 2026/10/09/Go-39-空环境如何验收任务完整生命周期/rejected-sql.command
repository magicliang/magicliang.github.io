psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 54089 -U admin -d go39live -Atc "SELECT count(*) FROM go_tasks WHERE input_text='overload'"
