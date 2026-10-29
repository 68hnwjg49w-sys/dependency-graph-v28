"""Точка входа инструмента визуализации графа зависимостей."""

import argparse
import sys
import urllib.request

from src.config import load_config
from src.errors import AppError, ConfigError
from src.graph import build_graph
from src.npm import NpmRepository
from src.testrepo import FileRepository

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_DATA_ERROR = 3
DEFAULT_CONFIG = "config.ini"
NO_DEPENDENCIES = "нет зависимостей"


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


def make_source(config, opener=urllib.request.urlopen):
    """Выбирает источник: файл тестового репозитория или реестр npm."""
    if config.test_mode:
        return FileRepository.load(config.repository)
    return NpmRepository(config.repository, opener)


def print_graph(graph, name_filter):
    """Выводит граф: зависимости каждого пакета, исключения и циклы."""
    print("Граф зависимостей пакета {} (обход в глубину):".format(
        graph.root))
    for name, dependencies in graph.edges.items():
        print("  {} -> {}".format(
            name, ", ".join(dependencies) or NO_DEPENDENCIES))
    print("Пакетов в графе: {}".format(len(graph.edges)))
    if graph.excluded:
        print("Исключены фильтром '{}': {}".format(
            name_filter, ", ".join(graph.excluded)))
    if not graph.cycles:
        print("Циклических зависимостей нет")
        return
    print("Циклические зависимости ({}):".format(len(graph.cycles)))
    for cycle in graph.cycles:
        print("  " + " -> ".join(cycle))


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
        source = make_source(config, opener)
        graph = build_graph(config.package, source, config.name_filter)
    except ConfigError as error:
        report_config_error(error)
        return EXIT_CONFIG_ERROR
    except AppError as error:
        print("ошибка: {}".format(error), file=sys.stderr)
        return EXIT_DATA_ERROR
    print_graph(graph, config.name_filter)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
