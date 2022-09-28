#!/bin/bash

if grep -q 'source /opt/autoenv/activate.sh' ~/.bashrc; then
    echo -e "\033[31m Автозагрузка среды Python \033[0m"
else
    echo -e "\033[31m Автоматическое обновление не поддерживается, см. http://docs.jumpserver.org/zh/docs/upgrade.html Обновляйтесь вручную \033[0m"
    exit 0
fi

source ~/.bashrc

cd `dirname $0`/ && cd .. && ./jms stop

jumpserver_backup=/tmp/jumpserver_backup$(date -d "today" +"%Y%m%d_%H%M%S")
mkdir -p $jumpserver_backup
cp -r ./* $jumpserver_backup

echo -e "\033[31m Вам нужно создать резервную копию базы данных Jumpserver? \033[0m"
stty erase ^H
read -p "Нажмите Y, чтобы подтвердить резервное копирование, в противном случае нажмите другие клавиши, чтобы пропустить резервное копирование. " a
if [ "$a" == y -o "$a" == Y ];then
    echo -e "\033[31m База данных резервируется \033[0m"
    echo -e "\033[31m Пожалуйста, введите данные базы данных вручную \033[0m"
    read -p 'Пожалуйста, введите ip базы данных Jumpserver:' DB_HOST
    read -p 'Пожалуйста, введите порт базы данных Jumpserver:' DB_PORT
    read -p 'Пожалуйста, введите имя базы данных Jumpserver:' DB_NAME
    read -p 'Пожалуйста, введите пользователя, у которого есть разрешение на экспорт базы данных:' DB_USER
    read -p 'Пожалуйста, введите пароль этого пользователя:' DB_PASSWORD
    mysqldump -h$DB_HOST -P$DB_PORT -u$DB_USER -p$DB_PASSWORD $DB_NAME > /$jumpserver_backup/$DB_NAME$(date -d "today" +"%Y%m%d_%H%M%S").sql || {
        echo -e "\033[31m Не удалось создать резервную копию базы данных, проверьте наличие ошибок \033[0m"
        exit 1
    }
    echo -e "\033[31m Резервное копирование базы данных завершено \033[0m"
else
    echo -e "\033[31m Операция резервного копирования базы данных отменена \033[0m"
fi

git pull && pip install -r requirements/requirements.txt && cd utils && sh make_migrations.sh

cd .. && ./jms start all -d
echo -e "\033[31m Пожалуйста, проверьте, успешно ли запущен jumpserver \033[0m"
echo -e "\033[31m Файлы резервных копий хранятся в каталоге $jumpserver_backup. \033[0m"
stty erase ^?

exit 0
