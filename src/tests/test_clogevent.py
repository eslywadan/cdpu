from dpam.acctclog import app, db
import os, sqlite3, json


def test_post_log_event():
    with app.test_client() as client:
        mock_event = {
            "event_type": "login",
             "actor": {
                "user_id": "u1234",
                 "username": "alice",
                 "ip": "192.168.1.10"
            },
         "target": {
                "service": "auth_service",
                 "resource": "login_page"
            },
         "action": "user_login",
         "outcome": "success",
         "context": {
                 "user_agent": "Mozilla/5.0",
                 "location": "Taipei",
                 "client_id": "web"
             },
        }

        response = client.post('/log/event', json=mock_event)
        return {"status_code": response.status_code,"resp_json": response.get_json}


def test_sql_engine():
    with app.app_context():
        db.create_all()
    base_dir = app.config['BASEDIR']
    with app.app_context():
        dbengine = db.engine
    dbname = dbengine.url.database.split('\\')[-1]
    print( f"Engine Path {dbengine.name}:///{base_dir}\\{dbname}")
    file_path = f"{base_dir}\\{dbname}"
    assert os.path.exists(file_path)
    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM log_event order by id desc limit 1")
    row = cursor.fetchone()
    if row:
        print(" Last log entry found")
        print(f"ID:{row[0]}, Timestamp: {row[1]}")
        print("Event Type:", row[2])
        print("Actor", json.loads(row[3])['user_id'])
    else:
        print("There is not log event found")
    conn.close()
    
    

if __name__ == '__main__':
    tc1 = test_post_log_event()
    assert tc1["status_code"] == 201
    request_json = tc1["resp_json"] 