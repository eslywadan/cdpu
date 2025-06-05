# Account Man api



##
## get a client with requested permission

- accounts_registries = db.select_accounts_registry_for_owner(user_id, resp_type="df")
```text
>>> accounts_registries
              CLIENT_ID                               REGISTRY          CREATE_DTTM
0                   mfg  /mfg,/retrain,-/retrain/cds/*/pipeviz  2022-03-14 14:22:36
1                   eng                      /eng,/retrain,/ml  2022-05-03 13:49:20
2  test_reg_retrain_cds                           /retrain/cds  2024-06-26 05:30:00
3         ml365_da_test                          /eng,/retrain  2024-09-09 02:55:55
4            test_samv4                                   None  2024-12-09 09:10:18
5               caruxPd                                   None  2025-03-07 05:15:39
6                  apds                            /carux/apds  2025-03-18 04:02:32

```

