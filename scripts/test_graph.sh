#!/bin/sh
# Демонстрация этапа 3: граф зависимостей на тестовых репозиториях.
# Интернет не нужен: пакеты описаны в файлах repos/*.txt.
cd "$(dirname "$0")/.." || exit 1

for file in configs/test/*.ini configs/test/errors/*.ini; do
    echo
    echo "Конфигурация $file:"
    sed -n '1s/^; //p' "$file"
    grep '^filter = .' "$file"
    repo=$(sed -n 's/^repository = //p' "$file")
    echo "Тестовый репозиторий $repo:"
    grep -v '^#' "$repo" | sed 's/^/    /'
    ./run.sh --config "$file" 2>&1
    echo "код завершения: $?"
done
