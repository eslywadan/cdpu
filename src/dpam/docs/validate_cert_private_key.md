# Validate certificate file

- validate certificate pem
should show certificate details without errirs
```bash
[user@HP08448W dataapiaccount]$ openssl x509 -in ./config/certificate.pem -text -noout
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number:
            4f:3f:08:40:e6:3c:41:e4:38:0a:5b:56:69:fb:9a:b6:bd:3d:75:4d
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: CN = localhost
        Validity
            Not Before: Mar 11 07:18:25 2025 GMT
            Not After : Mar 11 07:18:25 2026 GMT
        Subject: CN = localhost
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                Public-Key: (2048 bit)
                Modulus:
                    00:c8:6a:c0:2f:d8:ff:04:c8:ab:ce:e4:0e:fc:71:
                    8e:34:73:28:09:4d:e9:2a:a4:89:f3:fe:fc:1a:4e:
                    f1:fd:77:6d:9a:8b:e5:bf:b7:0b:c1:ca:5c:fb:00:
                    b7:e3:8b:df:bd:54:b6:8f:2d:85:b3:47:c6:ed:24:
                    3f:70:db:74:16:47:8d:9d:13:27:88:9a:23:ca:ad:
                    68:fe:54:d2:d6:f5:cc:4e:93:43:ee:e3:16:18:30:
                    e5:f5:61:bf:5a:91:c2:ea:0a:c3:16:91:40:43:1e:
                    33:66:54:57:79:83:f0:8f:43:65:f9:8f:c1:44:e9:
                    ab:2c:79:5d:d0:a4:0c:37:30:8a:2a:81:54:28:51:
                    7d:77:65:2d:82:42:f9:26:c2:4f:50:71:0d:e4:63:
                    e2:a1:18:15:ae:9f:6d:33:3b:34:fe:97:e2:cc:c7:
                    0b:46:87:1c:90:38:8d:e0:f7:09:cd:59:08:18:a8:
                    e5:39:88:7b:fc:7a:08:69:0c:5c:18:3a:28:9a:90:
                    b6:ee:84:82:47:dd:a6:21:a2:9c:0e:d1:ca:b9:5d:
                    cc:90:53:fc:a5:eb:b4:08:ad:18:09:30:c5:ec:35:
                    3b:86:3d:79:de:0f:73:f7:c3:a0:05:59:4a:95:57:
                    37:f6:92:e4:22:39:44:b2:6f:64:5e:3a:f4:a9:d1:
                    4d:99
                Exponent: 65537 (0x10001)
        X509v3 extensions:
            X509v3 Subject Key Identifier:
                CD:97:21:0D:E0:0D:41:5E:8F:A8:68:FF:13:AF:39:4D:EB:89:1E:8B
            X509v3 Authority Key Identifier:
                CD:97:21:0D:E0:0D:41:5E:8F:A8:68:FF:13:AF:39:4D:EB:89:1E:8B
            X509v3 Basic Constraints: critical
                CA:TRUE
    Signature Algorithm: sha256WithRSAEncryption
    Signature Value:
        4d:e7:0d:e4:10:42:94:c9:22:fe:c9:51:aa:66:d2:7b:fd:88:
        eb:12:27:04:46:d5:37:79:e1:3e:82:59:23:86:1b:2e:2f:fb:
        8d:9d:76:6a:0d:d0:24:62:2b:9c:cf:f5:ea:0b:00:a5:6f:a7:
        13:6d:69:77:b5:2d:0f:4b:ac:fd:df:fc:c8:26:75:72:c2:64:
        fe:5f:fa:08:75:6d:09:6b:49:7d:03:46:27:4e:5f:70:97:87:
        29:df:b7:ee:5c:84:b7:17:c2:73:ac:f5:c5:da:af:d9:2a:0a:
        5b:ee:fc:de:2b:e3:2d:c2:1c:f1:ee:8c:59:45:19:6d:55:84:
        ec:84:ce:69:f2:af:15:08:be:a7:a5:09:b7:3d:bf:ba:61:64:
        5e:76:71:24:86:ee:ab:71:ed:cc:49:22:4c:15:19:95:e2:45:
        fb:5a:40:66:b1:ef:e9:05:fb:e9:c4:b8:b7:ed:5d:7f:af:d3:
        f3:34:b3:5c:c5:45:56:76:3e:85:41:13:19:40:a0:10:f4:02:
        26:38:5a:6a:14:17:9b:72:8b:62:66:58:2a:ae:83:92:5f:c2:
        69:93:c0:d1:26:e0:53:a5:b2:e2:2d:1c:95:78:e0:bf:17:23:
        2d:26:87:0f:2e:0e:32:ab:57:aa:05:27:b9:f9:68:6f:ff:96:
        3f:c4:43:d6

```

```bash
[user@HP08448W dataapiaccount]$ openssl rsa -in ./config/mycminl.key -check
Enter pass phrase for ./config/mycminl.key:
RSA key ok
writing RSA key
-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC+Ws/haRuKVIgL
HqJ8xWTBmt4hzHlTdJDNV2VdkBhUuS9uW5fUaxjFNq8Wfz7Ur1iV1f8ltk8ODxbS
FiDeMmdUNtikEHGGsHUcZV6JdDniP4wOqKRK9Bwted3t31CEUK4BPdKBlywlldRG
UHDPZMqq7CKAigpedNCH1NR2cxklhoBOE2mii4PXN4Jw7tefe0VEgz1cgV5BKieY
0gcup9NJ5OOURuMire9qO/tPqiGWjnUO/P+oFcygepfmcALQNQcmXBm+pJyLcwzt
zEzSlKPo0YTvFaS4aZzwsOsrFR8nW5Z0eWQ86YyiWGNuw/NcmIx85S+gmD1mUIld
rrBz5KUhAgMBAAECggEAe5RTT0DAi27Tn3x0+tHf1r0nJwQrZB3SAC2T9kkdMqvC
+j9mc5ZPz4Dv7IgRj1yDA0uZyK7x5euv4hZRok9Qu+Cbhu/R9CJM9XFuDYiyJ4sf
70hW2P5f6LosdUi8ahpCzTWIm288Tu5VkIyaoFoMJSkGQTLdBnOKChUHFhslITFw
9FawVProZae262iMfCkJn4zNQ5BV8QSW5Ebokm+9ZRsTQ2eU0DIgaoDyxATWyUzO
/fh3cJlfRFs55cKZBoV10ldPpIWshD3JlVB+KMcLTW4gHF2VZwuPe+EBxul5LycP
rVvYdWAlVRXwDkS4FmZ0t6cuS2vEMAGk42TI3v4XTQKBgQDlfHFsbGGqfnhuqJGQ
aoieFddj2yYXwSwTZbVsb0G2mJV+sPVbzeUv400yRcKPnEqHzLSCZLq3NVmcWe3E
CS3yn5S2qzFK1gXv9wY1d4rdyTyP4IdzfykL5W3CIXiy6xTBF7IuiMkzQcq03F1C
01xRzaly7j/d3Zx+AaWGdFoo9wKBgQDUWPj1gYX9Olk1RyMaBA008snt2ifvtd7T
6omSLXOgguGPUOqy7L8qZSC0qOQOuwxoRnfYfZaXZAB7447VdRS2XRM5S7lyFHqf
QLVtesORi4i4wLYAVrkciuhLpzKPsfWTmfkAIlDXRFCLKUy5gas1tTiDKmroUrDZ
nJxiJJx0pwKBgCnqGsVU3lnHk7OSclPQQXeuQZLpegGotKYuU36kq3nwUI29QHMu
HggrGfRurWSRhUNcbjPKthe0VNOr0TOXAZ9o6j6a8fvbL2Zu1eF6HhD4KmmU9uhv
d03G788fUe5L5ZSHAXJiZW1JPP7fqOEFvbzrNWHahiu9yFFzd4ohQj5tAoGADX0V
W2r92ucQ8ZxyM13chOeDQjOgY862t9lnIbz3YlPOBi+KqRD217eSy0cLLZBeKmWH
iV346eb1TOlYkmCcjzT8WqBfyEpau7D9lVW+BInLhojfRsg7e/+q39tgD9arFdQr
CAImBnaVczGNaR8+g+veCh7wqY9PIpObL3TJ53MCgYAIFjeazidxIkRN+CTnFkb8
OUkmml5Pnz73pacGHa8P8xzNFRFxMO4SNHgE6VEyfKqGPonPWKQl9shV9z5cas+j
q/ZU89ikph81aeH8vxQBhQh3GeEnCDHNAl+c4EJQ/JvwrSDIXALK4S3LpRjnrWPS
j+XIPcxSpgszQMT1bi08QQ==
-----END PRIVATE KEY-----
```

- Verify Key and Cert Match: Calculate the modulus of both the certificate and the private key and compare them, They must be the same for the pair to be valid.

```bash
[user@HP08448W dataapiaccount]$ openssl x509 -noout -modulus -in ./config/mycminl.pem | openssl md5
Enter pass phrase for PKCS12 import pass phrase:
MD5(stdin)= 2cd21b275ee9c4819097ce7e00634deb
```

```bash
[user@HP08448W dataapiaccount]$ openssl rsa -noout -modulus -in ./config/mycminl.key | openssl md5
Enter pass phrase for ./config/mycminl.key:
MD5(stdin)= 2cd21b275ee9c4819097ce7e00634deb
```

## Trouble shooting

### server side
```bash
(lvenv) [user@HP08448W dataapiaccount]$ gunicorn --certfile=config/certificate.pem --keyfile=config/private-key
.pem -b localhost:8443 account_portal:app
[2025-03-11 16:53:17 +0800] [538022] [INFO] Starting gunicorn 23.0.0
[2025-03-11 16:53:17 +0800] [538022] [INFO] Listening at: https://127.0.0.1:8443 (538022)
[2025-03-11 16:53:17 +0800] [538022] [INFO] Using worker: sync
[2025-03-11 16:53:17 +0800] [538033] [INFO] Booting worker with pid: 538033
current env is set as prd
current env is set as prd
```

### client side
```bash
[user@HP08448W dataapiaccount]$ curl --verbose --insecure https://127.0.0.1:8443
* processing: https://127.0.0.1:8443
*   Trying 127.0.0.1:8443...
* Connected to 127.0.0.1 (127.0.0.1) port 8443
* ALPN: offers h2,http/1.1
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, CERT verify (15):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
* TLSv1.3 (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* ALPN: server did not agree on a protocol. Uses default.
* Server certificate:
*  subject: CN=localhost
*  start date: Mar 11 07:18:25 2025 GMT
*  expire date: Mar 11 07:18:25 2026 GMT
*  issuer: CN=localhost
*  SSL certificate verify result: self-signed certificate (18), continuing anyway.
* using HTTP/1.x
> GET / HTTP/1.1
> Host: 127.0.0.1:8443
> User-Agent: curl/8.2.1
> Accept: */*
>
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
* TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
* old SSL session ID is stale, removing
< HTTP/1.1 404 NOT FOUND
< Server: gunicorn
< Date: Tue, 11 Mar 2025 08:57:56 GMT
< Connection: close
< Content-Type: text/html; charset=utf-8
< Content-Length: 207
< Access-Control-Allow-Origin: *
<
<!doctype html>
<html lang=en>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>
* Closing connection
* TLSv1.3 (OUT), TLS alert, close notify (256):
```




### certfile=config/mycminl.pem & keyfile=config/mycminl.key
- server side
```bash
(lvenv) [user@HP08448W dataapiaccount]$ gunicorn --certfile=config/mycminl.pem --keyfile=config/mycminl.key -b localhost:8443 account_portal:app
```


- client side test
```bash
[user@HP08448W dataapiaccount]$ curl --verbose --insecure https://127.0.0.1:8443/account
* processing: https://127.0.0.1:8443/account
*   Trying 127.0.0.1:8443...
* Connected to 127.0.0.1 (127.0.0.1) port 8443
* ALPN: offers h2,http/1.1
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* OpenSSL/3.1.4: error:0A00010B:SSL routines::wrong version number
* Closing connection
curl: (35) OpenSSL/3.1.4: error:0A00010B:SSL routines::wrong version number
```