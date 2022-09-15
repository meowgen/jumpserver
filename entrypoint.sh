#!/bin/bash
function cleanup()
{
    local pids=`jobs -p`
    if [[ "${pids}" != ""  ]]; then
        kill ${pids} >/dev/null 2>/dev/null
    fi
}
# проверка
mkdir temp
cd temp
git clone https://github.com/meowgen/jumpserver.git
cp jumpserver/apps/ /opt/jumpserver/ -r -f
cd /opt/jumpserver
rm -rf temp

action="${1-start}"
service="${2-all}"

trap cleanup EXIT
if [[ "$action" == "bash" || "$action" == "sh" ]];then
    bash
elif [[ "$action" == "sleep" ]];then
    echo "Sleep 365 days"
    sleep 365d
else
    python jms "${action}" "${service}"
fi

