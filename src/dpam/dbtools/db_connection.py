import os
import sqlite3
from dpam.tools.config_loader import ConfigLoader

class DbConnection:
    _db_list = []
    _default_db_id = 0

    #取得預設的DB連線
    @classmethod
    def default(clz):
        clz.check_db_config()
        return clz.connection(clz._default_db_id)


    #以DB id，產生DB connection instance
    @classmethod
    def connection(clz, db_id):
        clz.check_db_config()

        db_info = clz._db_list[db_id]
        func_name = f'get_{db_info["type"]}_connection'
        func = getattr(clz, func_name)
        connection = func(db_info["connection_string"], db_info["driver_path"])
        return connection


    @classmethod
    def check_db_config(clz):
        if len(clz._db_list) == 0:
            db_config = ConfigLoader.config("database")
            clz._db_list = db_config["database_list"]
            clz._default_db_id = db_config["default"]


    @classmethod
    def reset_db_config(clz):
        clz._db_list = []
        clz._default_db_id = 0


    #以connection string, driver path，直接產生DB connection instance
    @staticmethod
    def get_sqlite_connection(connection_string, driver_path):
        # print(f"connectoin String: {connection_string} / driver_path: {driver_path}")
        return sqlite3.connect(connection_string)

