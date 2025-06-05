from tools.validate_user import RedisDb ,UserSessions


def get_session_key(count=0):
    if count == 0 : 
        session_key = "12345678"
        count += 1
    else: session_key = "abcdefg"
    return f"{session_key}"


sess_key = get_session_key()
user_id = 'qs.chou'
emp_id = '10135399'
UserSessions.add_login_user(sess_key, user_id, emp_id)
assert UserSessions.get_login_user_redis(user_id)["sess_key"] == sess_key
print(f"sess_key:{sess_key}")
kwargs = {"ext_info":"a super user"}
UserSessions.update_login_user_redis(user_id,**kwargs)

assert UserSessions.get_login_user_redis(user_id,kws=["ext_info"]) == kwargs 

sess_key = get_session_key(1) # simulate renew token, while the history ext info is kept
UserSessions.add_login_user(sess_key, user_id, emp_id)
assert UserSessions.get_login_user_redis(user_id,kws=["ext_info"]) == kwargs 
print(f"sess_key:{sess_key}")
print(f"It is still {kwargs['ext_info']}")