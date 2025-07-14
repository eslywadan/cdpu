# Data Catalog - Hive  Meta Store


```container
podman run -d \
    -e HIVE_METASTORE_DB_TYPE=postgres \
    -e HIVE_METASTORE_HOSTNAME=_postgres_host \
    -e HIVE_METASTORE_DB_NAME=hive
```