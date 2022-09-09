# Базовый образ alpine (лёгкий линукс)
FROM alpine:3.11

# Копирует файлы из этой папки в /opt/xpack
COPY . /opt/xpack

WORKDIR /opt/xpack
# Заглушка, чтобы образ работал, потому что докеру нужно, чтобы была CMD
CMD tail -f /dev/null