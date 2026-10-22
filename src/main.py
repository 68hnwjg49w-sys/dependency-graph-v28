"""Точка входа инструмента визуализации графа зависимостей."""

import argparse
import sys
import urllib.request

from src.config import load_config
from src.errors import AppError, ConfigError
from src.npm import get_direct_dependencies

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_REPOSITORY_ERROR = 3
DEFAULT_CONFIG = "config.ini"
TEST_MODE_LATER = (
    "режим тестового репозитория (test_mode = true) будет поддержан "
    "на этапе 3; сейчас зависимости получаются только по URL"
)


def parse_arguments(argv=None):
    """Разбирает аргументы командной строки: путь к файлу INI."""
    parser = argparse.ArgumentParser(
        prog="depgraph",
        description="Граф зависимостей пакетов npm.",
    )
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG, metavar="PATH",
        help="путь к конфигурационному файлу INI (по умолчанию "
             "config.ini)",
    )
    return parser.parse_args(argv)


def collect(config, opener=urllib.request.urlopen):
    """Получает версию и прямые зависимости пакета по URL репозитория."""
    if config.test_mode:
        raise AppError(TEST_MODE_LATER)
    return get_direct_dependencies(config.repository, config.package, opener)


def print_dependencies(package, version, dependencies):
    """Выводит все прямые зависимости по алфавиту: имя и диапазон версий."""
    print("Пакет: {} {}".format(package, version))
    if not dependencies:
        print("Прямых зависимостей нет")
        return
    print("Прямые зависимости ({}):".format(len(dependencies)))
    for name, versions in sorted(dependencies.items()):
        print("  {} {}".format(name, versions))


def report_config_error(error):
    """Печатает все ошибки конфигурации в поток ошибок."""
    print("ошибка конфигурации:", file=sys.stderr)
    for message in error.messages:
        print("  - " + message, file=sys.stderr)


def main(argv=None, opener=urllib.request.urlopen):
    """Запускает приложение и возвращает код завершения процесса."""
    args = parse_arguments(argv)
    try:
        config = load_config(args.config)
        version, dependencies = collect(config, opener)
    except ConfigError as error:
        report_config_error(error)
        return EXIT_CONFIG_ERROR
    except AppError as error:
        print("ошибка: {}".format(error), file=sys.stderr)
        return EXIT_REPOSITORY_ERROR
    print_dependencies(config.package, version, dependencies)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
