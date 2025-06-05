from flask import Flask, render_template, request, json, make_response, redirect
import dpam.db_access as db
import dpam.tools.validate_user as validate_user
from dpam.tools import account
# from flask_cors import CORS

app = Flask(__name__)
# CORS(app)

@app.route('/')
def get_index_page():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()
    
    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    response = make_response(render_template('index.html', user_id=user_id, is_admin=validate_user.is_admin(user_id), msg_type=msg_type, message = message))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response


@app.route('/accounts_for_admin')
def browse_accounts():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = "/accounts_for_admin"
    
    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_accounts_for_admin()
    response = make_response(render_template('accounts_for_admin.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

        
@app.route('/accounts_for_owner')
def browse_owner_accounts():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    sess = validate_user.UserSessions.get_session(sess_key)
    sess["list_page"] = "/accounts_for_owner"

    msg_type = request.args["msg_type"] if "msg_type" in request.args else ""
    message = db.DBResult[request.args["db_result"]].value if "db_result" in request.args else ""

    accounts = db.select_accounts_for_owner(user_id)
    response = make_response(render_template('accounts_for_owner.html', accounts = json.dumps(accounts), msg_type=msg_type, message = message, user_id=user_id))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response


@app.route('/create')
def create_account():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('create_account.html', client_id = "", error = "", user_id = user_id, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@app.route('/insert' , methods=['POST'])
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


@app.route('/edit/<string:client_id>')
def edit_account_for_admin(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    account = db.select_account_for_admin(client_id)
    if account is None:
        account = {'CLIENT_ID':'', 'EXPIRY':'', 'PERMISSION':'', 'OBSOLETE':False, 'REGISTRY':''}
        error = "Client Account not found!"
    else:
        error = ""

    response = make_response(render_template('edit_account.html', account = account, error = error, list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response
        
@app.route('/update', methods=['POST'])
def update_account_for_admin():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        expiry = request.form["txt_expiry"] if "txt_expiry" in request.form else ""
        registry = request.form["txt_registry"] if "txt_registry" in request.form else ""
        permissions = []
        if "chk_perm_query" in request.form:
            permissions.append("QUERY") 
        if "chk_perm_debug" in request.form:
            permissions.append("DEBUG") 
        if "chk_perm_admin" in request.form:
            permissions.append("ADMIN") 
        permission = "|".join(permissions)

        obsolete = "chk_obsolete" in request.form
        
        db_result = db.update_account(client_id, expiry, permission, obsolete, registry)

        return redirect("/accounts_for_admin?msg_type=success&db_result="+db_result.name)

    except Exception as err:
        account = db.select_account_for_admin(client_id)
        return render_template('edit_account.html', account = account, error = err.args[0], list_page = validate_user.get_list_page())


@app.route('/delete/<string:client_id>')
def delete_account(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('delete_account.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response
        
@app.route('/db_delete', methods=['POST'])
def db_delete_account():
    try:
        list_page = validate_user.get_list_page()
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        db_result = db.delete_account(client_id)
        return redirect(list_page + "?msg_type=success&db_result="+db_result.name)
    except Exception as err:
        return render_template('delete_account.html', client_id = client_id, error = err.args[0], list_page = list_page)

@app.route('/change_password/<string:client_id>')
def change_password(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('change_password.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@app.route('/db_change_password', methods=['POST'])
def db_change_password():
    try:
        client_id = request.form["txt_client_id"] if "txt_client_id" in request.form else ""
        password = request.form["txt_password"] if "txt_password" in request.form else ""
        password2 = request.form["txt_password2"] if "txt_password2" in request.form else ""

        error = "Please confirm your password again!" if password != password2 or password == "" else ""
        if error == "":
            db_result = db.change_password(client_id, password)
            return redirect("/accounts_for_owner?msg_type=success&db_result="+db_result.name)
        
    except Exception as err:
        error = err.args[0]

    return render_template('change_password.html', client_id = client_id, error = error, list_page = validate_user.get_list_page())


@app.route('/request_apikey/<string:client_id>')
def request_apikey(client_id):
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('request_apikey.html', client_id = client_id, error = "", list_page = validate_user.get_list_page()))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response

@app.route('/grpc_get_apikey', methods=['POST'])
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

@app.route('/copy_demo')
def copy_demo():
    (user_id, sess_key) = validate_user.validate_user()
    if user_id is None: return validate_user.redirect_to_login()

    response = make_response(render_template('copy_demo.html'))

    if sess_key is not None: validate_user.write_session_cookie(response, sess_key)
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3400)