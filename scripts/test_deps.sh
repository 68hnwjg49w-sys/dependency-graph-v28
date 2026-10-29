#!/bin/sh
# Демонстрация работы с реестром npm: графы зависимостей пакетов
# и ошибки получения данных.
# Нужен доступ в интернет к https://registry.npmjs.org.
cd "$(dirname "$0")/.." || exit 1

for file in configs/debug.ini configs/react.ini config.ini \
        configs/express.ini; do
    echo
    echo "Конфигурация $file:"
    sed -n '1s/^; //p' "$file"
    grep -E '^(package|filter) =' "$file"
    ./run.sh --config "$file" 2>&1
    echo "код завершения: $?"
done

for file in configs/fetch_errors/*.ini; do
    echo
    echo "Ошибка получения данных, $file:"
    sed -n '1s/^; //p' "$file"
    ./run.sh --config "$file" 2>&1
    echo "код завершения: $?"
done

echo
echo "Ошибка конфигурации по-прежнему проверяется:"
./run.sh --config configs/errors/bad_url.ini 2>&1
echo "код завершения: $?"
