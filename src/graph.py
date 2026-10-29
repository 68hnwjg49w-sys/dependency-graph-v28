"""Построение графа зависимостей обходом в глубину (DFS) с рекурсией.

Источник зависимостей — любой объект с методом dependencies(name),
который возвращает список имён прямых зависимостей пакета: реестр
npm или файл тестового репозитория.
"""

from dataclasses import dataclass, field

from src.errors import GraphError


@dataclass
class DependencyGraph:
    """Граф зависимостей: рёбра, исключённые пакеты и найденные циклы."""

    root: str
    edges: dict = field(default_factory=dict)
    excluded: list = field(default_factory=list)
    cycles: list = field(default_factory=list)


def is_excluded(name, name_filter):
    """Проверяет, содержит ли имя пакета подстроку фильтра."""
    return bool(name_filter) and name_filter in name


def build_graph(root, source, name_filter=""):
    """Строит граф зависимостей пакета root с учётом транзитивности."""
    if is_excluded(root, name_filter):
        raise GraphError(
            "анализируемый пакет '{}' содержит подстроку фильтра "
            "'{}'".format(root, name_filter)
        )
    graph = DependencyGraph(root)
    _visit(root, source, name_filter, graph, [])
    return graph


def _visit(name, source, name_filter, graph, path):
    """Рекурсивно обходит зависимости пакета name (DFS).

    path — пакеты на текущем пути от корня. Ребро в пакет из path
    означает цикл: оно сохраняется в графе, но обход по нему не идёт.
    Каждый пакет обходится один раз.
    """
    graph.edges[name] = []
    path.append(name)
    for dependency in source.dependencies(name):
        if is_excluded(dependency, name_filter):
            _remember(graph.excluded, dependency)
            continue
        graph.edges[name].append(dependency)
        if dependency in path:
            start = path.index(dependency)
            graph.cycles.append(path[start:] + [dependency])
        elif dependency not in graph.edges:
            _visit(dependency, source, name_filter, graph, path)
    path.pop()


def _remember(items, name):
    """Добавляет имя в список, если его там ещё нет."""
    if name not in items:
        items.append(name)
