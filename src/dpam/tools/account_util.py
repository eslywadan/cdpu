from dpam.tools.account import Account
from dpam.db_access import update_account_registry, delete_account
from dpam.tools.logger import Logger, LogLevel
from datetime import datetime

def set_log(_key=""):
    Logger._level = LogLevel.INFO
    _time = datetime.now().strftime("%H%M%S")
    log_keyname = f"account_legacy_transform_{_time}_{_key}"
    Logger.default(keyname=log_keyname)
    Logger.log(f"Begin account legacy data validation and transformation")
    print(f"Logger path {Logger._filename}")
    return Logger

Logger = set_log()

def init_account_table(opType=1, log=Logger):
    """
    if opType == 1 : (As-is account is the legacy data)
        1. Copy as-is account data as account_old, 
        2. recreated a new account, 
        3. create default client ids by system owner
        4. import legacy data
    if opType == 2 : (Have existed legacy data in account_old)
        1. recreated a new account,
        2. creat default client ids by system owner
        3. import legacy data
    """
    log.log(f"init account table with opType {opType}")
    # ReCreate table
    if opType == 1: 
        Account._convert_account_table(move_legacy_data=False)
        log.log(f"Move existed account data to account_old")
    if opType == 2:
        # Drop & Recreate table
        Account.drop_table_if_exists('account')
        Account.create_table()
        log.log(f"recreate the account table")
    create_system_objects()
    log.log("Create the system objects")
    Account.insert_legacy_data()
    log.log("Move the legacy data back to account")
    
def create_system_objects(log=Logger):
    # Createa base resources
    Account._create_base_resources()
    log.log("Create base resources")
    # Create base group and role with resources registry value
    Account._create_base_group()
    log.log("Create base group")
    Account._create_base_role()
    log.log("Create base role")
    Account._create_typical_user()
    log.log("Create typical user")

def validate_resource_clients(log=Logger):
    resources = Account._get_resource_clients_all_info()
    for idx, cid in resources['CLIENT_ID'].items():
       val_auto_correct_client(log,cid,1)
       
def validate_group_clients(log=Logger):
    groups = Account._get_group_clients_all_info()
    for idx, cid in groups['CLIENT_ID'].items():
        val_auto_correct_client(log, cid, 3)

def validate_role_clients(log=Logger):
    roles = Account._get_role_clients_all_info()
    for idx, cid in roles['CLIENT_ID'].items():
        val_auto_correct_client(log, cid, type=4)

def validate_user_clients(log=Logger):
    users = Account._get_user_clients_all_info()
    for idx, cid in users['CLIENT_ID'].items():
        val_auto_correct_client(log, cid, type=2)
 
def validate_base_groups(log=Logger):
    # Validate registry value of base group and role
    for base_group in Account.base_groups:
        group_id = base_group["CLIENT_ID"]
        val_auto_correct_client(log, group_id, 3) 

def validate_base_roles(log=Logger):        
    for base_role in Account.base_roles:
        role_id = base_role["CLIENT_ID"]
        val_auto_correct_client(log,role_id,4)

def validate_typical_users(log=Logger):
    # Validate typical user
    for typical_user in Account.typical_users:
        user_id = typical_user["CLIENT_ID"]
        user = val_auto_correct_client(log, user_id, type=2)
        user.validate_none_resource_client_registry_value()
        log.log(f'Typical User ID: {user_id} has bind_group {user._bindGrp} and bind_role {user._bindRole}')
        for _grp in user._bindGrp.split(','):
            grp = val_auto_correct_client(log, _grp, 3)
            assert grp._registry in user._registry
        for _role in user._bindRole.split(','):
            role = val_auto_correct_client(log, _role, type=4)
            assert role._registry in user._registry
        log.log(f'Typical User ID: {user_id} has registry value {user._registry}')
        
def val_auto_correct_client(log, client_id, type):
    _client = Account(clientId=client_id, type=type)
    if type in [2, 3, 4]:
        log.log(f"validate {_client.clientid} with type {_client.type}")
        val_resp = _client.validate_none_resource_client_registry_value(log=log)
        ac_resp = _client.auto_correct_none_resource_client_registry_value(log=log)
        log.log(f"validate result {val_resp}")
        log.log(f"auto correct result {ac_resp}")
    if type == 1:
        log.log(f"validate resoruce {_client.clientid}")
        resp = _client.validate_resource_client_reg_value(log=log)
        log.log(resp)
    _client.set_client_registry()
    return _client
        
# Test _find_best_match_res()
def test_find_best_match_res(new_res = "/ds/retrain/abc"):
    new_res_reg_ = Account._get_res_client_registry_info(new_res)
    if new_res_reg_['REGISTRY'] != {}:
        _bm_res = Account._find_best_match_res(new_res)
        assert new_res in _bm_res 
        delete_account(new_res,type=1)
        
    _bm_res = Account._find_best_match_res(new_res)
    assert new_res not in _bm_res
    ## delete resource account id =  "/ds/retrain/abc" type = 1 if exist
    append_reg = Account._resource_clientid_reg_value(_bm_res[0],new_res)[1]
    new_reg_ = f"{_bm_res[1]},{append_reg}"
    update_account_registry(client_id=_bm_res[0], registry= new_reg_, type=1)
    Account._create_if_not_exist(client_id=new_res,registry='*')
    delete_account(new_res,type=1)
    _bm_res = Account._find_best_match_res(new_res)
    assert new_res not in _bm_res


def tranform_legacy_table():
    # Test transform table
    init_account_table()
    validate_base_groups()
    validate_base_roles()
    validate_typical_users()
    validate_resource_clients()
    validate_group_clients()
    validate_role_clients()
    validate_user_clients()

    test_find_best_match_res()
    

