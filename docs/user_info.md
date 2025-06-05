# User Info
經由認證機制 (ssov4) 回傳的使用者的資訊(User Info)有 AD (user_id) 帳號與 工號 (emp_id)，此外，ssov4 會同時回傳一個 Token，取此 Token 的末25至末5碼做為 session_key，此 session_key 存在名為 'session_api_account' 的使用者 cookie 內。使用者對此 app 發出請求時，即會夾帶此 cookie，可以藉由 request.cookies.get('session_api_account') 得到該使用者的  session_key，或藉由 request.cookie.set('session_api_account') 設定該 cookie 名稱的值。此 cookie 的值會隨者使用者的 Token 更新，進行更新，也就是它的有效生命週期是跟著 Token。即使用者若使用不同的 Token 登入，此 session_key 也會隨著更新。 
## write_session_cookie() to set the session_key & get_session_cookie() to get the session_key
每當使用者成功登入時，此 ap  會在 response 物件內夾帶 cookie 的對應值，該值會在使用者接收回應，儲存在使用者的 cookie 內。而每次在發出請求時，此 cookie  值會跟著 request  物件發出，因而可以從 request 內得到該 cookie 的值。

## UserSessions and Redis
在獲得 ssov4 回傳的資訊取得 User Info，以 session_key 作為鍵值，將 User Info 存在 UserSesssions 此類別。該類別定義一個 _sessions 的字典類別屬性，做為儲存點。
以此 _sessions 作為儲存 user info 的好處可以避免使用者的機敏資訊外洩，然而 UserSessions 的資料容易揮發，因此需要將該資訊儲存在一個相對不易揮發的地方，即 redis。儲存資料的時機在 呼叫 UserSessions.add_login_user() 方法時，在使用者資料加入後，亦將資料存在 redis。呼叫時，亦透過 UserSessions 取用，若 _sessions 內的資料揮發了，則會從 redis 所存的備分檔取用。 

儲存在 redis 的資訊，會有 _sessions 的資料，亦可以透過 UserSessions 此類別的兩個方法，update_login_user_redis() 以及 get_login_user_redis() 以 user_id 為鍵值存取以字典型態紀錄的任意資訊。


## redis cache

若要取用 redis cache 的 user info，標準做法先取得 session_key，呼叫 get_session_key() 的方法，即可以從使用者的 cookie 內得到 session_key。取得 session_key 後，即可呼叫 UserSessions.get_login_user(session_key) 得到 user_id，亦可以直接呼叫 UserSession.get_login_user()，不帶 session_key 的呼叫，會自動呼叫 get_session_key() 方法得到 session_key。

取得 user_id 後，即可呼叫 UserSessions.get_login_user_redis(user_id)，即會回傳該 user_id 在 redis 所儲存的資訊。


