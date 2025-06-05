from dpam.tools.account import Account
from dpam.tools.logger import Logger, LogLevel

## Below code is used for validating and correcting the legacy registy

Logger._level = LogLevel.INFO
log_keyname = "account_legacy_transform"
Logger.default(keyname=log_keyname)
Logger.log(f"Begin account legacy data validation and transformation")
print(f"Logger path {Logger._folder_path[0]}//{Logger._filename}")
assert Logger._keyname == log_keyname

groups = Account._get_group_clients_all_info()
for idx, cid in groups['CLIENT_ID'].items():
  group = Account(cid, type=3)
  res = group.auto_correct_none_resource_client_registry_value(log=Logger)
  Logger.log(res)

roles = Account._get_role_clients_all_info()
for idx, cid in roles['CLIENT_ID'].items():
  role = Account(cid, type=4)
  res = role.auto_correct_none_resource_client_registry_value(log=Logger)
  Logger.log(res)

users = Account._get_user_clients_all_info()
for idx, cid in users['CLIENT_ID'].items():
  user = Account(cid, type=2)
  res = user.auto_correct_none_resource_client_registry_value(log=Logger)
  Logger.log(res)
  
resources = Account._get_resource_clients_all_info()
for idx, cid in resources['CLIENT_ID'].items():
  resource = Account(cid, type=1)
  res = resource.validate_resource_client_reg_value(log=Logger)
  Logger.log(res)
