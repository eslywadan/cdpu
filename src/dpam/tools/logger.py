import os
import datetime as dt
import logging
import enum
from dpam.tools.config_loader import ConfigLoader


#6個等級的log level
class LogLevel(enum.IntEnum):
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0


class Logger:
    _level = LogLevel.NOTSET
    _folder_path = ["logs"]
    _keyname = "apiaccount"

    #取得預設的logger instance
    @classmethod
    def default(clz,keyname=None):
        clz.check_log_config()
        if keyname: clz._keyname = keyname
        return clz.logger(clz._level)

    #確保_folder_path與_level有值
    @classmethod
    def check_log_config(clz):
        if clz._level == LogLevel.NOTSET:
            log_config = ConfigLoader.config("log")
            clz._folder_path = log_config["folder_path"]
            clz._level = LogLevel[log_config["level"]]

    @classmethod
    def reset_log_config(clz):
        clz._level = LogLevel.NOTSET
        clz._folder_path = "ext"


    #產生logger instance
    @classmethod
    def logger(clz, level, keyname=None):
        clz.check_log_config()

        today = dt.datetime.today()
        key = f'{clz._keyname}_{today:%Y-%m-%d}_{level.name}'
        logger = logging.getLogger(key)
        if len(logger.handlers)==0:
            logger.setLevel(level.value)

            filename = os.path.join(*clz._folder_path, f'{key}.log')
            clz._filename = filename
            handler = logging.FileHandler(filename)
        
            log_format = '%(asctime)s %(levelname)s: %(message)s'
            date_format = '%Y-%m-%d %H:%M:%S'
            handler.setFormatter(logging.Formatter(log_format, date_format))
            logger.addHandler(handler)

        return logger

    #方便的log function
    @classmethod
    def log(clz, msg):
        logger = clz.default()
        logger.info(msg)
