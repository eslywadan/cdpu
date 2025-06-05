from dpam.tools.config_loader import ConfigLoader
from dsbase.tools.redis_db import RedisDb
from dpam.tools.logger import Logger
from dpam.dbtools.db_connection import DbConnection


def reset_config():
    ConfigLoader.reset_config_loader()
    RedisDb.reset_cache_config()
    Logger.reset_log_config()
    DbConnection.reset_db_config()
