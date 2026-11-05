#!/bin/sh
# Этап 4: сравнение порядка загрузки с реальным менеджером пакетов npm.
# Запуск: sh scripts/compare_npm.sh [пакет], по умолчанию express.
# Нужны интернет и npm (Node.js). npm здесь используется только для
# сравнения результатов, сама программа его не вызывает.
cd "$(dirname "$0")/.." || exit 1
package=${1:-express}

if ! command -v npm > /dev/null 2>&1; then
    echo "npm не найден: установите Node.js с https://nodejs.org"
    exit 1
fi

work="out/compare_$(printf '%s' "$package" | tr '@/' '__')"
rm -rf "$work"
mkdir -p "$work"
printf '[settings]\npackage = %s\nrepository = %s\noutput = graph.svg\n' \
    "$package" "https://registry.npmjs.org" > "$work/config.ini"

echo "1. Порядок загрузки по нашей программе:"
./run.sh --config "$work/config.ini" --load-order > "$work/ours_full.txt" \
    || exit 1
cat "$work/ours_full.txt"
sed -n 's/^ *[0-9]*\. //p' "$work/ours_full.txt" | sort > "$work/ours.txt"

echo
echo "2. Разрешение зависимостей настоящим npm (без скачивания пакетов):"
(cd "$work" && npm init -y > /dev/null \
    && npm install "$package" --package-lock-only --ignore-scripts \
        --no-audit --no-fund) || exit 1

LIST_LOCK='
const lock = require(require("path").resolve(process.argv[1]));
for (const [path, info] of Object.entries(lock.packages)) {
    if (!path) continue;
    const name = path.slice(path.lastIndexOf("node_modules/") + 13);
    const nested = path.split("node_modules/").length > 2;
    console.log(name, info.version, nested ? "(вложенный: " + path + ")" : "");
}'
echo
echo "3. Пакеты в package-lock.json npm (порядок файла — по алфавиту путей):"
node -e "$LIST_LOCK" "$work/package-lock.json" | tee "$work/npm_full.txt"
cut -d' ' -f1,2 "$work/npm_full.txt" | sort > "$work/npm.txt"
cut -d' ' -f1 "$work/ours.txt" | sort -u > "$work/ours_names.txt"
cut -d' ' -f1 "$work/npm.txt" | sort -u > "$work/npm_names.txt"

echo
echo "4. Сравнение:"
echo "пакетов у нас: $(wc -l < "$work/ours_names.txt" | tr -d ' ')," \
    "у npm: $(wc -l < "$work/npm.txt" | tr -d ' ')" \
    "(разных имён: $(wc -l < "$work/npm_names.txt" | tr -d ' '))"
echo "Есть только у нас:"
comm -23 "$work/ours_names.txt" "$work/npm_names.txt" | sed 's/^/  /'
echo "Есть только у npm:"
comm -13 "$work/ours_names.txt" "$work/npm_names.txt" | sed 's/^/  /'
echo "Разные версии (пакет, наша версия, версия npm):"
join "$work/ours.txt" "$work/npm.txt" | awk '$2 != $3 {print "  " $0}'
