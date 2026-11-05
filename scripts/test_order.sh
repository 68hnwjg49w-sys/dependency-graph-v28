#!/bin/sh
# Демонстрация этапа 4: порядок загрузки зависимостей на тестовых
# репозиториях. Интернет не нужен.
cd "$(dirname "$0")/.." || exit 1

for name in basic chain single cycle self_cycle cycles filter big; do
    file="configs/test/$name.ini"
    echo
    echo "Конфигурация $file:"
    sed -n '1s/^; //p' "$file"
    grep '^filter = .' "$file"
    repo=$(sed -n 's/^repository = //p' "$file")
    echo "Тестовый репозиторий $repo:"
    grep -v '^#' "$repo" | sed 's/^/    /'
    ./run.sh --config "$file" --load-order 2>&1
    echo "код завершения: $?"
done

echo
echo "Ошибка в тестовом репозитории — порядок не строится:"
./run.sh --config configs/test/errors/missing.ini --load-order 2>&1
echo "код завершения: $?"
