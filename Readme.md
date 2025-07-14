# Core Data Plateform Utilities

![image](./docs/png/core_plateform_utilities.png)

## pack and install on developing
run `pack_intall_cdpu.py` after code change. 
`--install_option=1 or 2`, if 1, it will install directly from the source without generating the package files.
                           if 2, it will build the pack and install from the buid pack.
`--clean_legacy_dir=True or False`, the option is used when `install_option=2`. If 'True' (default), it will clean the legacy folders in ['build', 'dist'] or will keep legacy versions.

```bash
python -m pack_install_dpam 
python -m pack_install_dpam --install_option=1
python -m pack_install_dpam --install_option=2 --clean_legacy_dir=True
```
- `pack_install_dpam` arguments 
`--install_option, required=False, default=2,
    help="1: install from source wo build packs 2: build and install from build pack"
--clean_legacy_dir, required=False, default=True,help="True: Will clean the legacy dirs (build and dist folders) False:keep legacy files"`    
`


## am module (Account Management)
There are two blue prints /account and /api at the host services.
### /account
data studio api account management allow user to create his/her owned client id to use services provided by data studio.
Also, admins use the same app to maintain privileges of those client ids.
### /api 
- /apikey Authorized by client id and password
- /user Authorized by ssotoken, will get the user's ad name by ssotoken
- /user/clients Authorized by ssotoken, will the client ids created by the user 
- /user/permits/client Authorized by ssotoken, will select a client that has the required permits, return None if there is not the client 
- /user/permits/client/apikey Authorized by ssotoken, will select a client that has the required permits, generate an apikey to represent the client
- /vapikey 
- /{client}/apikey Authorized by ssotoken

### app id is 'api_account'
the app id 'api_account' is used in the prefix of cookie's name and the prefix of redis key to user's ext info.
### os.environ
os.environ["api_account_env"] is 'prod'|'test' or else. 
- validate_user use this env to switch the 'prod'|'test' sso api from samv4 
os.environ['configpath'] is where the config.json reside


## testing env
Prequist: Case when finished development, and the installatiion file has generated. [installation file location](./dist/) 
- Copy the installation file onto the mount folder at innoloud (such as \\tncloudnas\datastudio-ci-dev-ds-ci-dev-ext-01$\test\dataapigrpc\account\dist)
- Needs to update the \\tncloudnas\datastudio-ci-dev-ds-ci-dev-ext-01$\test\dataapigrpc\account\init_dpam.sh to correct the installation file's version.
```bash
python -m pip install dist/dsbase-250325.164719-py3-none-any.whl
python -m pip install dist/dpam-250326.121909-py3-none-any.whl
gunicorn --bind 0.0.0.0:8080 dpam.account_portal:app --log-file /app/ext/gunicorn.log --timeout 900
```
- restart container after update