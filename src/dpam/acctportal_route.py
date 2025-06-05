from flask import Flask, render_template, request, json, make_response, redirect, url_for
import dpam.db_access as db
import dpam.tools.validate_user as validate_user
from dpam.tools import account
from flask import Blueprint
from dpam.tools.logger import Logger
from dpam.tools.account import Account
from dpam.blueprint_create import acct_bp as account_bp

# app = Flask(__name__)
# account_bp = Blueprint('acct_bp', __name__)

@account_bp.route('/')
def get_index_page():
    (user_id, sess_key) = validate_user.validate_user(token_required=True)
    if user_id is None: return validate_user.redirect_to_login()
    
    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    response = make_response(render_template('index.html', user_id=user_id, is_admin=validate_user.is_admin(user_id), msg_type=msg_type, message = message))
    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/ssov4')
def ssov4():
    """
    base route require token attached with the request. If a user has not the token attached, it will be redirect
    to sso's log-in page. SSO will check if exist the effective token and reuse it or let user re-log-in to get a fresh token
    """
    (user_id, sess_key) = validate_user.validate_user(token_required=True)
    if user_id is None: return validate_user.redirect_to_login()
    Logger.log(f"ssov4: user_id is {user_id} type: {type(user_id)}")
    response = make_response(render_template('ssov4_simple.html', user_id=user_id ))
    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/session')
def session():
    """
    base route is not require token attached with the request. 
    it will reuse the cookie's data as well. 
    """
    (user_id, sess_key) = validate_user.validate_user(token_required=False)
    if user_id is None: return validate_user.redirect_to_login()
    Logger.log(f"ssov4: user_id is {user_id} type: {type(user_id)}")
    response = make_response(render_template('ssov4_simple.html', user_id=user_id ))
    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/accounts_for_admin')
def browse_accounts():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = url_for('acct_bp.browse_accounts') #"/account/accounts_for_admin"
    
    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_accounts_for_admin()
    response = make_response(render_template('accounts_for_admin.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

        
@account_bp.route('/accounts_for_owner')
def browse_owner_accounts():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = url_for('acct_bp.browse_owner_accounts') #"/account/accounts_for_owner"

    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_accounts_for_owner(user_id)
    Logger.log(f"list accounts created by {user_id}/accounts: {accounts}")
    response = make_response(render_template('accounts_for_owner.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message, user_id=user_id))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response


@account_bp.route('/create')
def create_account():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('create_account.html', client_id = "", error = "", user_id = user_id, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/insert' , methods=['POST'])
def insert_account():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        password = request.form["txt_password"] if "txt_password" in request.form else ""
        password2 = request.form["txt_password2"] if "txt_password2" in request.form else ""
        user_id = request.form["txt_user_id"] if "txt_user_id" in request.form else ""
            
        error = "Client ID cannot be blank! " if client_id == "" else ""
        error += "Please confirm your password again!" if password != password2 or password == "" else ""
        list_page = validate_user.get_list_page()
        if error == "":
            db_result = db.insert_account(client_id, password, user_id)
            return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
            
    except Exception as err:
        error = err.args[0]

    return render_template('create_account.html', client_id = client_id, error = error, user_id = user_id, list_page = list_page)


@account_bp.route('/edit/<string:client_id>')
def edit_account_for_admin(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    account = db.select_account_for_admin(client_id)
    if account is None:
        account = {'CLIENT_ID':'', 'EXPIRY':'', 'PERMISSION':'', 'OBSOLETE':False, 'REGISTRY':'', 'BIND_ROLE':'', 'BIND_GROUP':''}
        error = "Client Account not found!"
    else:
        error = ""
    
    #20250514 新增查詢Group/Role的Resource Id (client_id), 並傳送至網頁
    get_role_clients = Account._get_role_clients_all_info()
    get_group_clients = Account._get_group_clients_all_info()
    role_clientIds = [{'id': v, 'text': v} for v in get_role_clients['CLIENT_ID'].values()]
    group_clientIds = [{'id': v, 'text': v} for v in get_group_clients['CLIENT_ID'].values()]
    response = make_response(render_template('edit_account.html', account = account, error = error, list_page = validate_user.get_list_page(), role_clientIds=role_clientIds, group_clientIds=group_clientIds))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response
        
@account_bp.route('/update', methods=['POST'])
def update_account_for_admin():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        expiry = request.form["txt_expiry"] if "txt_expiry" in request.form else ""
        registry = request.form["txt_registry"] if "txt_registry" in request.form else ""

        #20250514 取得Group/Role值
        #bind_role = request.form["txt_bind_role"] if "txt_bind_role" in request.form else ""
        #bind_group = request.form["txt_bind_group"] if "txt_bind_group" in request.form else ""
        selected_role = request.form.getlist("txt_bind_role")
        bind_role =  ",".join(selected_role) if selected_role else ""
        selected_group = request.form.getlist("txt_bind_group")
        bind_group =  ",".join(selected_group) if selected_group else ""
        
        permissions = []
        if "chk_perm_query" in request.form:
            permissions.append("QUERY") 
        if "chk_perm_debug" in request.form:
            permissions.append("DEBUG") 
        if "chk_perm_admin" in request.form:
            permissions.append("ADMIN") 
        permission = "|".join(permissions)

        obsolete = "chk_obsolete" in request.form
        
        #20250514 檢查registry是否符合格式/規則
        if registry != "":
            #registry最後的字元若是逗號，則去掉
            if registry[-1] == ",": registry = registry[:-1]
            account_obj = Account(client_id, 2) 
            check_registry_result = account_obj.validate_none_resource_client_registry_value(registry.split(','))
            print("registry = %s" % registry)
            # 判斷 invalid 是否有值 或 status 是否為 False
            if check_registry_result.get("invalid") or check_registry_result.get("status") == False:
                # 有錯誤，回傳頁面並帶入錯誤訊息
                if check_registry_result.get("invalid"):
                    error_message = "registry內容有不符：" + ", ".join(check_registry_result["invalid"]) + "\n" + check_registry_result.get("message", "")
                elif check_registry_result.get("message"):
                    error_message = "Error: " + check_registry_result.get("message")
                raise Exception(error_message)        
        
        db_result = db.update_account(client_id, expiry, permission, obsolete, registry, bind_group, bind_role)

        return redirect("/account/accounts_for_admin?msg_type=success&db_result="+db_result.name)

    except Exception as err:
        account = db.select_account_for_admin(client_id)
        #20250514 新增查詢Group/Role的Resource Id (client_id), 並傳送至網頁
        get_role_clients = Account._get_role_clients_all_info()
        get_group_clients = Account._get_group_clients_all_info()
        role_clientIds = [{'id': v, 'text': v} for v in get_role_clients['CLIENT_ID'].values()]
        group_clientIds = [{'id': v, 'text': v} for v in get_group_clients['CLIENT_ID'].values()]
        return render_template('edit_account.html', account = account, error = err.args[0], list_page = validate_user.get_list_page(), role_clientIds=role_clientIds, group_clientIds=group_clientIds)


@account_bp.route('/delete/<string:client_id>')
def delete_account(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('delete_account.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response
        
@account_bp.route('/db_delete', methods=['POST'])
def db_delete_account():
    try:
        list_page = validate_user.get_list_page()
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        db_result = db.delete_account(client_id)
        return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
    except Exception as err:
        return render_template('delete_account.html', client_id = client_id, error = err.args[0], list_page = list_page)

@account_bp.route('/change_password/<string:client_id>')
def change_password(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('change_password.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/db_change_password', methods=['POST'])
def db_change_password():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        password = request.form["txt_password"] if "txt_password" in request.form else ""
        password2 = request.form["txt_password2"] if "txt_password2" in request.form else ""

        error = "Please confirm your password again!" if password != password2 or password == "" else ""
        if error == "":
            db_result = db.change_password(client_id, password)
            return redirect("/account/accounts_for_owner?msg_type=success&db_result="+db_result.name)
        
    except Exception as err:
        error = err.args[0]

    return render_template('change_password.html', client_id = client_id, error = error, list_page = validate_user.get_list_page())


@account_bp.route('/request_apikey/<string:client_id>')
def request_apikey(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('request_apikey.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/grpc_get_apikey', methods=['POST'])
def grpc_get_apikey():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        password = request.form["txt_password"] if "txt_password" in request.form else ""
        apikey = ""
        error = "Please confirm your password again!" if password == "" else ""
        if error == "":
            
            apikey = account.get_client_apikey_grpc(client_id, password)
            print("%s,%s,%s", apikey.clientid, apikey.apikey, apikey.expiry)
            # return redirect("/accounts_for_owner?msg_type=success&db_result="+db_result.name)
            # apikey = "YuGoTahaPP"
            return render_template('request_apikey.html', client_id = client_id, apikey = apikey.apikey, list_page = validate_user.get_list_page())
        
    except Exception as err:
        error = err.args[0]

    return render_template('request_apikey.html', client_id = client_id, error = error, list_page = validate_user.get_list_page())

@account_bp.route('/copy_demo')
def copy_demo():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('copy_demo.html'))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

# role & group
# 新增角色或群組
@account_bp.route('/create_group_role')
def create_group_role():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('create_group_role.html', client_id = "", error = "", user_id = user_id, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/insert_group_role', methods=['POST'])
def insert_group_role():
    try:        
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        type = request.form["txt_type"] if "txt_type" in request.form else ""
        register = request.form["txt_registry"] if "txt_registry" in request.form else ""
        #type值先轉大寫，若為ROLE，則轉換為4；若為GROUP，則轉換為3
        #type = 4 if type.upper() == "ROLE" else 3
        
        error = "Client ID cannot be blank! " if client_id == "" else ""
        #error += "Registry cannot be blank! " if register == "" else ""
        list_page = validate_user.get_list_page()
        if error == "":
            db_result = db.insert_group_role(client_id, type, register)
            return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
            
    except Exception as err:
        error = err.args[0]

    return render_template('create_group_role.html', client_id = client_id, error = error, user_id = user_id, list_page = list_page)

# 更新registry & expiry
@account_bp.route('/edit_group_role/<string:client_id>/<string:type>')
def edit_group_role_for_admin(client_id, type):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    account = db.select_group_role_for_admin(client_id, type)
    if account is None:
        account = {'CLIENT_ID':'', 'CREATE_DTTM':'', 'REGISTRY':'', 'TYPE':''}
        error = "Role not found!" if type == 4 else "Group not found!"
    else:
        error = ""

    response = make_response(render_template('edit_group_role.html', account = account, error = error, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/update_group_role', methods=['POST'])
def update_group_role_for_admin():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        #expiry = request.form["txt_expiry"] if "txt_expiry" in request.form else ""
        registry = request.form["txt_registry"] if "txt_registry" in request.form else ""
            
        type = request.form["txt_type"] if "txt_type" in request.form else ""
        #type值先轉大寫，若為ROLE，則轉換為4；若為GROUP，則轉換為3     
        if type.upper() == "ROLE":
            type = 4
        elif type.upper() == "GROUP":
            type = 3
        
        #20250514 檢查registry是否符合格式/規則
        if registry != "":
            #registry最後的字元若是逗號，則去掉
            if registry[-1] == ",": registry = registry[:-1]
            account_obj = Account(client_id, type) 
            check_registry_result = account_obj.validate_none_resource_client_registry_value(registry.split(','))
            print("registry = %s" % registry)
            print("check_registry_result = %s" % check_registry_result)
            # 判斷 invalid 是否有值 或 status 是否為 False
            if check_registry_result.get("invalid") or check_registry_result.get("status") == False:
                # 有錯誤，回傳頁面並帶入錯誤訊息
                if check_registry_result.get("invalid"):
                    error_message = "registry內容有不符：" + ", ".join(check_registry_result["invalid"]) + "\n" + check_registry_result.get("message", "")
                elif check_registry_result.get("message"):
                    error_message = "Error: " + check_registry_result.get("message")
                raise Exception(error_message)      

        db_result = db.update_group_role(client_id, type, registry)
        return redirect("/account/group_role_for_admin?msg_type=success&db_result="+db_result.name)

    except Exception as err:
        account = db.select_group_role_for_admin(client_id, type)
        return render_template('edit_group_role.html', account = account, error = err.args[0], list_page = validate_user.get_list_page())

# 刪除角色或群組
@account_bp.route('/delete_group_role/<string:client_id>/<string:type>')
def delete_group_role(client_id, type):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('delete_group_role.html', client_id = client_id, type = type, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/db_delete_group_role', methods=['POST'])
def db_delete_group_role():
    try:
        list_page = validate_user.get_list_page()
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        type = request.form["txt_type"] if "txt_type" in request.form else ""
        #type值先轉大寫，若為ROLE，則轉換為4；若為GROUP，則轉換為3
        if type.upper() == "ROLE":
            type = 4
        elif type.upper() == "GROUP":
            type = 3
        db_result = db.delete_group_role(client_id, type)
        return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
    except Exception as err:
        return render_template('delete_group_role.html', client_id = client_id, error = err.args[0], list_page = list_page)
 
# 查詢角色或群組
@account_bp.route('/group_role_for_admin')
def browse_group_role():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = url_for('acct_bp.browse_group_role') #"/account/group_role_for_admin"

    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_groups_roles_for_admin()
    response = make_response(render_template('group_role_for_admin.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response


# Resource
# 查詢Resource
@account_bp.route('/resource_for_admin')
def browse_resource():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = url_for('acct_bp.browse_resource') #"/account/resource_for_admin"

    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_resources_for_admin()
    response = make_response(render_template('resource_for_admin.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

# 新增資源
@account_bp.route('/create_resource')
def create_resource():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('create_resource.html', client_id = "", error = "", user_id = user_id, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/insert_resource', methods=['POST'])
def insert_resource():
    try:        
        (user_id, sess_key) = validate_user.validate_user()
        if user_id is None: return validate_user.redirect_to_login()

        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        type = 1 
        register = request.form["txt_registry"] if "txt_registry" in request.form else ""
        
        error = "Client ID cannot be blank! " if client_id == "" else ""
        #error += "Registry cannot be blank! " if register == "" else ""
        list_page = validate_user.get_list_page()
        if error == "":
            db_result = db.insert_resource(client_id, type, register, user_id)
            return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
            
    except Exception as err:
        error = err.args[0]

    return render_template('create_group_role.html', client_id = client_id, error = error, user_id = user_id, list_page = list_page)

# 更新registry & expiry
@account_bp.route('/edit_resource/<string:client_id>/<string:type>')
def edit_resource_for_admin(client_id, type):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()
    #針對__SLASH__轉換成/
    client_id = client_id.replace('__SLASH__', '/')
    print("client_id = %s, type = %s" %(client_id, type))
    
    account = db.select_resource_for_admin(client_id, type)
    if account is None:
        account = {'CLIENT_ID':'', 'CREATE_DTTM':'', 'REGISTRY':'', 'TYPE':''}
        error = "Resource not found!"
    else:
        error = ""

    response = make_response(render_template('edit_resource.html', account = account, error = error, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/update_resource', methods=['POST'])
def update_resource_for_admin():
    try:
        (user_id, sess_key) = validate_user.validate_user()
        if user_id is None: return validate_user.redirect_to_login()        
        
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        #expiry = request.form["txt_expiry"] if "txt_expiry" in request.form else ""
        registry = request.form["txt_registry"] if "txt_registry" in request.form else ""
        type = 1
        
        #20250514 檢查registry是否符合格式/規則
        if registry != "":
            #registry最後的字元若是逗號，則去掉
            if registry[-1] == ",": registry = registry[:-1]
            account_obj = Account(client_id, type) 
            check_registry_result = account_obj.validate_none_resource_client_registry_value(registry.split(','))
            print("registry = %s" % registry)
            print("check_registry_result = %s" % check_registry_result)
            # 判斷 invalid 是否有值 或 status 是否為 False
            if check_registry_result.get("invalid") or check_registry_result.get("status") == False:
                # 有錯誤，回傳頁面並帶入錯誤訊息
                if check_registry_result.get("invalid"):
                    error_message = "registry內容有不符：" + ", ".join(check_registry_result["invalid"]) + "\n" + check_registry_result.get("message", "")
                elif check_registry_result.get("message"):
                    error_message = "Error: " + check_registry_result.get("message")
                raise Exception(error_message)        
        
        db_result = db.update_resource(client_id, type, registry, user_id)

        return redirect("/account/resource_for_admin?msg_type=success&db_result="+db_result.name)

    except Exception as err:
        account = db.select_resource_for_admin(client_id, type)
        return render_template('edit_resource.html', account = account, error = err.args[0], list_page = validate_user.get_list_page())

# 刪除資源
@account_bp.route('/delete_resource/<string:client_id>/<string:type>')
def delete_resource(client_id, type):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()
    #針對__SLASH__轉換成/
    client_id = client_id.replace('__SLASH__', '/')
    response = make_response(render_template('delete_resource.html', client_id = client_id, type = type, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@account_bp.route('/db_delete_resource', methods=['POST'])
def db_delete_resource():
    try:
        list_page = validate_user.get_list_page()
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        type = 1
        db_result = db.delete_resource(client_id, type)
        return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
    except Exception as err:
        return render_template('delete_resource.html', client_id = client_id, error = err.args[0], list_page = list_page)
 


if __name__ == '__main__':
    account_bp.run(host='0.0.0.0', port=3400)