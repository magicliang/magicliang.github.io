psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 54089 -U admin -d go39live -c 'DROP TRIGGER delay_claim ON go_tasks; DROP FUNCTION delay_task_claim()'
