from datetime import datetime
import uuid
import hashlib

def get_account_token(client_id):
    #clock_seq = int(datetime.today().strftime("%H%M%S%f"))
    #return str(uuid.uuid1(clock_seq = clock_seq))

    dt = datetime.today().strftime("%Y-%m-%d")
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, client_id + "_" + dt))

def crypto_password(type, password):
    if type == 0:
        return password
    elif type == 1:
        hash_code = str(uuid.uuid5(uuid.NAMESPACE_DNS, password))
        return hash_code.replace("-", "b810")
    elif type == 2:
        sha1 = hashlib.sha1()
        sha1.update(password.encode("utf-8"))
        return sha1.hexdigest()
        
    return password