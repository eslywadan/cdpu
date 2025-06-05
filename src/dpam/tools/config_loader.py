import json
import os

class ConfigLoader:
    _config_all = {}

    @classmethod
    def config(cls, catalog):
        if len(cls._config_all) == 0:
            filename = os.path.join('config', 'config.json')
            with open(filename) as json_file:
                cls._config_all = json.load(json_file)
        
        return cls._config_all[catalog]


    @classmethod
    def reset_config_loader(cls):
        cls._config_all = {}
