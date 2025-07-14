# install cdpu packages
python3.12 -m pip install /app/dist/cdpu-250630.154549-py3-none-any.whl
cd app
python3.12 create_db.py
# python3.12 check_logs_db.py
gunicorn --bind 0.0.0.0:8080 dpem.event_api:app --log-file /app/ext/gunicorn.log --timeout 900