"""Точка входа инструмента визуализации графа зависимостей."""

import argparse
import sys

from src.config import load_config
from src.errors import ConfigError

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
DEFAULT_CONFIG = "config.ini"


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


def print_parameters(config):
    """Выводит все настраиваемые параметры в формате ключ = значение."""
    for key, value in config.items():
        print("{} = {}".format(key, value).rstrip())


def report_config_error(error):
    """Печатает все ошибки конфигурации в поток ошибок."""
    print("ошибка конфигурации:", file=sys.stderr)
    for message in error.messages:
        print("  - " + message, file=sys.stderr)


def main(argv=None):
    """Запускает приложение и возвращает код завершения процесса."""
    args = parse_arguments(argv)
    try:
        config = load_config(args.config)
    except ConfigError as error:
        report_config_error(error)
        return EXIT_CONFIG_ERROR
    print_parameters(config)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
