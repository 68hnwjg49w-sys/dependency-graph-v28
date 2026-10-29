"""Тестовый репозиторий: граф пакетов, описанный в текстовом файле.

Формат файла: одна строка на пакет, «ПАКЕТ: ЗАВИСИМОСТЬ ...».
Пакеты называются большими латинскими буквами, зависимости
разделяются пробелами. Пустые строки и строки с «#» пропускаются.
"""

import re

from src.errors import RepositoryError

NAME_PATTERN = re.compile(r"^[A-Z]+$")
COMMENT = "#"
SEPARATOR = ":"


class FileRepository:
    """Источник зависимостей — файл тестового репозитория."""

    def __init__(self, packages):
        """Запоминает словарь «пакет — список зависимостей»."""
        self.packages = packages

    @classmethod
    def load(cls, path):
        """Читает и разбирает файл тестового репозитория."""
        try:
            with open(path, encoding="utf-8") as stream:
                text = stream.read()
        except (OSError, UnicodeDecodeError) as error:
            raise RepositoryError(
                "не удалось прочитать файл {}: {}".format(path, error)
            ) from error
        return cls(parse_repository(text))

    def dependencies(self, package):
        """Возвращает прямые зависимости пакета из файла."""
        if package not in self.packages:
            raise RepositoryError(
                "пакет {} не найден в тестовом репозитории".format(package)
            )
        return list(self.packages[package])


def parse_repository(text):
    """Разбирает текст файла; при ошибках сообщает обо всех сразу."""
    packages, errors = {}, []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith(COMMENT):
            continue
        problem = _parse_line(line, packages)
        if problem:
            errors.append("строка {}: {}".format(number, problem))
    if errors:
        raise RepositoryError(
            "ошибки в файле тестового репозитория:\n  - "
            + "\n  - ".join(errors)
        )
    if not packages:
        raise RepositoryError("тестовый репозиторий пуст")
    return packages


def _parse_line(line, packages):
    """Разбирает строку «ПАКЕТ: ЗАВИСИМОСТИ»; возвращает ошибку или None."""
    name, separator, rest = line.partition(SEPARATOR)
    name = name.strip()
    if not separator:
        return "ожидается запись «ПАКЕТ: ЗАВИСИМОСТИ»"
    if not NAME_PATTERN.match(name):
        return "имя пакета — большие латинские буквы, получено " \
               "'{}'".format(name)
    if name in packages:
        return "пакет {} описан повторно".format(name)
    dependencies = rest.split()
    wrong = [item for item in dependencies if not NAME_PATTERN.match(item)]
    if wrong:
        return "имя зависимости — большие латинские буквы, получено " \
               "'{}'".format(wrong[0])
    packages[name] = list(dict.fromkeys(dependencies))
    return None
