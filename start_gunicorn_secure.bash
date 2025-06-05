gunicorn --certfile=config/mycminl.pem --keyfile=config/mycminl.key -b localhost:443 account_portal:account_portal --log-file gunicorn.log

# sudo /mnt/e/projects/dataapiaccount/lvenv/bin/gunicorn --certfile=config/mycminl.pem --keyfile=config/mycminl.key -b localhost:443 account_portal:account_portal --log-file gunicorn.log
# sudo /mnt/e/projects/dataapiaccount/lvenv/bin/gunicorn --certfile=./config/certificate.pem --keyfile=config/private-key.pem -
# b localhost:443 account_portal:app