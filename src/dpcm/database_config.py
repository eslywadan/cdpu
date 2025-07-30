"""
Config Management//Database Config
"""
from dsbase.tools.config_loader import ConfigLoader
from dsbase.tools.sec_loader import SecretLoader

def postgresql_config(env="ci-dev"):
    # ------ Configuration ------
    DB_USER = 'am'
    DB_PASSWORD = 'am_password'
    DB_HOST = '10.53.200.183'
    DB_PORT = '35467'
    DB_NAME = 'accountman'
    # postgres connection uri
    DATABASE_URL = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    return DATABASE_URL

