#!/bin/sh
# Демонстрация этапа 1: чтение конфигурации и обработка ошибок.
cd "$(dirname "$0")/.." || exit 1

echo "Конфигурация по умолчанию (config.ini):"
./run.sh
echo "код завершения: $?"

for file in configs/express.ini configs/test_mode.ini; do
    echo
    echo "Правильная конфигурация $file:"
    ./run.sh --config "$file"
    echo "код завершения: $?"
done

for file in configs/errors/*.ini; do
    echo
    echo "Ошибочная конфигурация $file:"
    sed -n '1s/^; //p' "$file"
    ./run.sh --config "$file" 2>&1
    echo "код завершения: $?"
done

echo
echo "Файл конфигурации не существует:"
./run.sh --config configs/no_such_file.ini 2>&1
echo "код завершения: $?"

echo
echo "Вместо файла указан каталог:"
./run.sh --config configs 2>&1
echo "код завершения: $?"

echo
echo "Пустой путь к файлу:"
./run.sh --config "" 2>&1
echo "код завершения: $?"

echo
echo "Неизвестный параметр командной строки:"
./run.sh --wat 2>&1
echo "код завершения: $?"
