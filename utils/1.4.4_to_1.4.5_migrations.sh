#!/bin/bash
# 

host=127.0.0.1
port=3306
username=root
db=jumpserver

echo "Резервное копирование исходных миграций"
mysqldump -u${username} -h${host} -P${port} -p ${db} django_migrations > django_migrations.sql.bak
ret=$?

if [ ${ret} == "0" ];then
    echo "Начать использовать новые миграции"
    mysql -u${username} -h${host} -P${port} -p ${db} < django_migrations.sql
else
    echo "Not valid"
fi


