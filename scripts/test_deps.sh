#!/bin/sh
# Демонстрация этапа 2: прямые зависимости пакетов npm по URL реестра.
# Нужен доступ в интернет к https://registry.npmjs.org.
cd "$(dirname "$0")/.." || exit 1

for file in config.ini configs/react.ini configs/babel_core.ini \
        configs/express.ini; do
    echo
    echo "Конфигурация $file:"
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
echo "Тестовый режим (будет реализован на этапе 3):"
./run.sh --config configs/test_mode.ini 2>&1
echo "код завершения: $?"

echo
echo "Ошибка конфигурации по-прежнему проверяется:"
./run.sh --config configs/errors/bad_url.ini 2>&1
echo "код завершения: $?"
