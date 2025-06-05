from dpam.dbtools.db_connection import DbConnection
import dpam.tools.crypto as crypto
from dpam.dbtools.sql_buffer import SqlBuffer
import pandas as pd
from datetime import datetime, timedelta
import enum

class DBResult(enum.Enum):
    CreateAccountOK='Create Account successfully!'
    UpdateAccountOK='Update Account successfully!'
    DeleteAccountOK='Delete Account successfully!'
    UpdatePasswordOK='Update password successfully!'
    NoAccountFound="No Account found!"
    CreateGroupOK='Create Group successfully!'
    CreateRoleOK='Create Role successfully!'
    UpdateGroupOK='Update Group successfully!'
    UpdateRoleOK='Update Role successfully!'
    DeleteGroupOK='Delete Group successfully!'
    DeleteRoleOK='Delete Role successfully!'
    DeleteFail='Delete Fail!'
    UpdateFail='Update Fail!'
    CreateResourceOK='Create Resource successfully!'
    UpdateResourceOK='Update Resource successfully!'
    DeleteResourceOK='Delete Resource successfully!'


def insert_account(client_id, password, user_id, type=2, valid_days=365.25*10, bind_group=None, bind_role=None):
    """
        account has default type == 2 indicates general users
                            type == 1 refers resources
                            type == 3 & 4 referes groups and roles 
    """
    type = type
    dttm = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    crypted_password = crypto.crypto_password(type, password)
    expiry = (datetime.today() + timedelta(valid_days)).strftime("%Y-%m-%d")
    sql = f'''
        INSERT INTO ACCOUNT (CLIENT_ID, PASSWORD, TYPE, EXPIRY, PERMISSION, OWNER_USER_ID, OBSOLETE, CREATE_DTTM, BIND_GROUP, BIND_ROLE) 
        VALUES('{client_id}', '{crypted_password}', '{type}', '{expiry}', 'QUERY', '{user_id}', 0, '{dttm}', '{bind_group}', '{bind_role}')'''

    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(sql)
    curs.close()
    cn.commit()
    cn.close()

    #return "Create Client ID successfully!"
    return DBResult.CreateAccountOK

def update_account(client_id, expiry, permission, obsolete, registry="", bind_group="", bind_role=""):
    sql = f"UPDATE ACCOUNT SET EXPIRY = '{expiry}', PERMISSION = '{permission}', OBSOLETE = {1 if obsolete else 0}, REGISTRY = '{registry}', BIND_ROLE = '{bind_role}', BIND_GROUP = '{bind_group}'"
    buf = SqlBuffer(sql).add("CLIENT_ID", client_id)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    #return "Update Client ID successfully!"
    return DBResult.UpdateAccountOK

def update_account_registry(client_id, registry="", type=2, consolidate=True):
    if consolidate: registry = consolidate_registry_value(registry)
    sql = f"UPDATE ACCOUNT SET REGISTRY = '{registry}'"
    buf = SqlBuffer(sql).add("CLIENT_ID", client_id)
    buf.add("TYPE", type)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    #return "Update Client ID successfully!"
    return DBResult.UpdateAccountOK

def consolidate_registry_value(_registry:str):
    """
    consolidate will do element trim and remove duplicate
    """
    items = [item.strip() for item in _registry.split(",")]
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return ",".join(result)

def delete_account(client_id,type=2):
    sql = 'DELETE FROM ACCOUNT'
    buf = SqlBuffer(sql).add("CLIENT_ID", client_id)
    buf.add("TYPE", type)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    return DBResult.DeleteAccountOK

def change_password(client_id, password):
    type = 2
    crypted_password = crypto.crypto_password(type, password)
    sql = f"UPDATE ACCOUNT SET PASSWORD = '{crypted_password}', TYPE = {type}"
    buf = SqlBuffer(sql).add("CLIENT_ID", client_id)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    return DBResult.UpdatePasswordOK

def select_account_for_admin(client_id):
    sql = 'SELECT CLIENT_ID, EXPIRY, PERMISSION, OBSOLETE, REGISTRY, BIND_GROUP, BIND_ROLE FROM ACCOUNT'
    buf = SqlBuffer(sql).add("CLIENT_ID", client_id)
    cn = DbConnection.default()
    df = pd.read_sql_query(buf.sql, cn)
    dict_list =  df.to_dict('records')

    return dict_list[0] if len(dict_list) > 0 else None

def select_accounts_for_admin():
    sql = 'SELECT CLIENT_ID, OWNER_USER_ID, CREATE_DTTM, EXPIRY, PERMISSION, OBSOLETE, BIND_GROUP, BIND_ROLE FROM ACCOUNT WHERE TYPE = 2'
    cn = DbConnection.default()
    df = pd.read_sql_query(sql, cn)
    dict_list =  df.to_dict('records')

    return dict_list

def select_accounts_for_owner(user_id,resp_type="records"):
    sql = 'SELECT CLIENT_ID, CREATE_DTTM FROM ACCOUNT'
    buf = SqlBuffer(sql).add("OWNER_USER_ID", user_id).add("TYPE", "2")
    cn = DbConnection.default()
    df = pd.read_sql_query(buf.sql, cn)
    dict_list =  df.to_dict('records')

    return dict_list if len(dict_list) > 0 else None

def select_accounts_registry_for_owner(user_id, resp_type="records"):
    sql = 'SELECT CLIENT_ID,REGISTRY, CREATE_DTTM FROM ACCOUNT'
    buf = SqlBuffer(sql).add("OWNER_USER_ID", user_id)
    cn = DbConnection.default()
    df = pd.read_sql_query(buf.sql, cn)
    dict_list =  df.to_dict(resp_type)

    return dict_list if len(dict_list) > 0 else None

#roles & groups
# 新增角色或群組
def insert_group_role(client_id, type, register):
    dttm = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    sql = f'''
        INSERT INTO ACCOUNT (CLIENT_ID, TYPE, REGISTRY, CREATE_DTTM) 
        VALUES('{client_id}', {type}, '{register}', '{dttm}')'''

    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(sql)
    curs.close()
    cn.commit()
    cn.close()
    
    if type == 4:
        return DBResult.CreateRoleOK
    else:
        return DBResult.CreateGroupOK
    
# 更新registry & expiry 
def update_group_role(client_id, type, registry):
    sql = f"UPDATE ACCOUNT SET REGISTRY = '{registry}' WHERE CLIENT_ID = '{client_id}' AND TYPE = {type}"
    buf = SqlBuffer(sql)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    if type == 4:
        return DBResult.UpdateRoleOK
    elif type == 3:
        return DBResult.UpdateGroupOK
    else:    
        return DBResult.UpdateFail
    
# 查詢角色或群組
def select_group_role_for_admin(client_id, type):
    sql = f"SELECT CLIENT_ID, CREATE_DTTM, REGISTRY, TYPE FROM ACCOUNT WHERE CLIENT_ID = '{client_id}' AND TYPE = {type}"
    buf = SqlBuffer(sql)
    cn = DbConnection.default()
    df = pd.read_sql_query(buf.sql, cn)
    dict_list =  df.to_dict('records')

    return dict_list[0] if len(dict_list) > 0 else None

def select_groups_roles_for_admin():
    sql = 'SELECT CLIENT_ID, CREATE_DTTM, REGISTRY, TYPE FROM ACCOUNT WHERE TYPE IN (3, 4)'
    cn = DbConnection.default()
    df = pd.read_sql_query(sql, cn)
    dict_list =  df.to_dict('records')

    return dict_list

# 刪除角色或群組 
def delete_group_role(client_id, type):
    sql = f"DELETE FROM ACCOUNT WHERE CLIENT_ID = '{client_id}' AND TYPE = {type}"
    buf = SqlBuffer(sql)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    if type == 4:
        return DBResult.DeleteRoleOK
    elif type == 3:    
        return DBResult.DeleteGroupOK
    else:
        return DBResult.DeleteFail


# resource
# 查詢資源
def select_resources_for_admin():
    sql = 'SELECT CLIENT_ID, TYPE, OWNER_USER_ID, CREATE_DTTM, REGISTRY FROM ACCOUNT WHERE TYPE = 1'
    cn = DbConnection.default()
    df = pd.read_sql_query(sql, cn)
    dict_list =  df.to_dict('records')

    return dict_list

def select_resource_for_admin(client_id, type):
    sql = f"SELECT CLIENT_ID, TYPE, OWNER_USER_ID, CREATE_DTTM, REGISTRY FROM ACCOUNT WHERE CLIENT_ID = '{client_id}' AND TYPE = {type}"
    buf = SqlBuffer(sql)
    cn = DbConnection.default()
    df = pd.read_sql_query(buf.sql, cn)
    dict_list =  df.to_dict('records')

    return dict_list[0] if len(dict_list) > 0 else None

# 新增資源
def insert_resource(client_id, type, register, user_id):
    dttm = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    sql = f'''
        INSERT INTO ACCOUNT (CLIENT_ID, TYPE, REGISTRY, OWNER_USER_ID, CREATE_DTTM) 
        VALUES('{client_id}', {type}, '{register}', '{user_id}', '{dttm}')'''

    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(sql)
    curs.close()
    cn.commit()
    cn.close()
    
    return DBResult.CreateResourceOK
    
# 更新registry & expiry 
def update_resource(client_id, type, registry, user_id):
    sql = f"UPDATE ACCOUNT SET REGISTRY = '{registry}', OWNER_USER_ID = '{user_id}' WHERE CLIENT_ID = '{client_id}' AND TYPE = {type}"
    buf = SqlBuffer(sql)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    return DBResult.UpdateResourceOK

# 刪除資源
def delete_resource(client_id, type):
    sql = f"DELETE FROM ACCOUNT WHERE CLIENT_ID = '{client_id}' AND TYPE = {type}"
    buf = SqlBuffer(sql)
    cn = DbConnection.default()
    curs = cn.cursor()
    curs.execute(buf.sql)
    curs.close()
    cn.commit()
    cn.close()

    return DBResult.DeleteResourceOK
