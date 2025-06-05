python -m pip install dist/dsbase-250325.164719-py3-none-any.whl
python -m pip install dist/dpam-250325.162401-py3-none-any.whl
gunicorn --bind 0.0.0.0:8080 dpam.account_portal:app --log-file /app/ext/gunicorn.log --timeout 900