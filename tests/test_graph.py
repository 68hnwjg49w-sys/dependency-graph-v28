"""Модульные тесты построения графа зависимостей (DFS)."""

import unittest

from src.errors import GraphError, RepositoryError
from src.graph import build_graph, is_excluded, load_order
from src.testrepo import FileRepository, parse_repository


def repository(text):
    """Создаёт тестовый репозиторий из текста."""
    return FileRepository(parse_repository(text))


class CountingSource:
    """Источник-обёртка: считает, сколько раз запрошен каждый пакет."""

    def __init__(self, source):
        """Запоминает исходный источник."""
        self.source = source
        self.calls = []

    def dependencies(self, name):
        """Запоминает запрос и передаёт его исходному источнику."""
        self.calls.append(name)
        return self.source.dependencies(name)


class FilterTest(unittest.TestCase):
    """Проверяет условие исключения пакета."""

    def test_substring(self):
        """Пакет исключается, если в имени есть подстрока."""
        self.assertTrue(is_excluded("XB", "X"))
        self.assertTrue(is_excluded("babel-core", "core"))
        self.assertFalse(is_excluded("B", "X"))

    def test_empty_filter(self):
        """Пустой фильтр ничего не исключает."""
        self.assertFalse(is_excluded("A", ""))


class BuildGraphTest(unittest.TestCase):
    """Проверяет обход в глубину и транзитивные зависимости."""

    def test_transitive_dependencies(self):
        """В граф попадают зависимости зависимостей."""
        graph = build_graph("A", repository("A: B\nB: C\nC: D\nD:\n"))
        self.assertEqual(graph.edges, {
            "A": ["B"], "B": ["C"], "C": ["D"], "D": [],
        })

    def test_depth_first_order(self):
        """Пакеты обходятся в глубину: B и его потомки раньше C."""
        graph = build_graph("A", repository(
            "A: B C\nB: D\nC: E\nD:\nE:\n"))
        self.assertEqual(list(graph.edges), ["A", "B", "D", "C", "E"])

    def test_shared_dependency_visited_once(self):
        """Общая зависимость запрашивается у источника один раз."""
        source = CountingSource(repository("A: B C\nB: D\nC: D\nD:\n"))
        graph = build_graph("A", source)
        self.assertEqual(source.calls, ["A", "B", "D", "C"])
        self.assertEqual(graph.edges["C"], ["D"])
        self.assertEqual(graph.cycles, [])

    def test_only_reachable_packages(self):
        """В граф попадают только пакеты, достижимые из корня."""
        graph = build_graph("B", repository("A: B\nB: C\nC:\nD:\n"))
        self.assertEqual(list(graph.edges), ["B", "C"])

    def test_no_dependencies(self):
        """Пакет без зависимостей — граф из одной вершины."""
        graph = build_graph("A", repository("A:\n"))
        self.assertEqual(graph.edges, {"A": []})


class CycleTest(unittest.TestCase):
    """Проверяет обработку циклических зависимостей."""

    def test_simple_cycle(self):
        """Цикл найден, обход завершается, ребро цикла сохранено."""
        source = CountingSource(repository("A: B\nB: C\nC: A D\nD:\n"))
        graph = build_graph("A", source)
        self.assertEqual(graph.cycles, [["A", "B", "C", "A"]])
        self.assertEqual(graph.edges["C"], ["A", "D"])
        self.assertEqual(source.calls, ["A", "B", "C", "D"])

    def test_self_dependency(self):
        """Пакет, зависящий сам от себя, — цикл из одной вершины."""
        graph = build_graph("A", repository("A: A B\nB:\n"))
        self.assertEqual(graph.cycles, [["A", "A"]])

    def test_several_cycles(self):
        """В графе может быть несколько циклов."""
        graph = build_graph("A", repository(
            "A: B C\nB: A\nC: D\nD: C\n"))
        self.assertEqual(graph.cycles, [["A", "B", "A"], ["C", "D", "C"]])

    def test_cycle_not_through_root(self):
        """Цикл может не проходить через корень."""
        graph = build_graph("A", repository("A: B\nB: C\nC: B\n"))
        self.assertEqual(graph.cycles, [["B", "C", "B"]])

    def test_visited_but_not_on_path_is_not_cycle(self):
        """Повторный приход в уже обойдённый пакет — не цикл."""
        graph = build_graph("A", repository("A: B C\nB: C\nC:\n"))
        self.assertEqual(graph.cycles, [])


class FilterGraphTest(unittest.TestCase):
    """Проверяет исключение пакетов по подстроке."""

    text = "A: B XB C\nB: XC\nC: D\nXB: E\nXC: D\nD:\nE:\n"

    def test_excluded_packages_not_analyzed(self):
        """Исключённые пакеты и их зависимости не анализируются."""
        source = CountingSource(repository(self.text))
        graph = build_graph("A", source, "X")
        self.assertEqual(graph.edges, {
            "A": ["B", "C"], "B": [], "C": ["D"], "D": [],
        })
        self.assertEqual(graph.excluded, ["XC", "XB"])
        self.assertNotIn("XB", source.calls)
        self.assertNotIn("E", source.calls)

    def test_filter_breaks_cycle(self):
        """Исключённый пакет разрывает цикл."""
        graph = build_graph("A", repository("A: B\nB: C\nC: A\n"), "C")
        self.assertEqual(graph.cycles, [])
        self.assertEqual(graph.excluded, ["C"])

    def test_root_matches_filter(self):
        """Корень с подстрокой фильтра — ошибка."""
        with self.assertRaisesRegex(GraphError, "подстроку фильтра"):
            build_graph("XA", repository("XA:\n"), "X")


class MissingPackageTest(unittest.TestCase):
    """Проверяет пакеты, которых нет в репозитории."""

    def test_missing_dependency(self):
        """Неописанная зависимость — ошибка при обходе."""
        with self.assertRaisesRegex(RepositoryError, "пакет B не найден"):
            build_graph("A", repository("A: B\n"))

    def test_missing_root(self):
        """Неописанный корень — ошибка."""
        with self.assertRaisesRegex(RepositoryError, "пакет Z не найден"):
            build_graph("Z", repository("A:\n"))


class LoadOrderTest(unittest.TestCase):
    """Проверяет порядок загрузки зависимостей."""

    def order(self, text, root="A", name_filter=""):
        """Строит граф из текста и возвращает порядок загрузки."""
        return load_order(build_graph(root, repository(text), name_filter))

    def assert_dependencies_first(self, text, order):
        """Каждый пакет стоит после всех своих зависимостей."""
        packages = parse_repository(text)
        position = {name: index for index, name in enumerate(order)}
        for name in order:
            for dependency in packages[name]:
                if dependency in position:
                    self.assertLess(position[dependency], position[name])

    def test_chain(self):
        """Цепочка загружается с конца."""
        self.assertEqual(self.order("A: B\nB: C\nC:\n"), ["C", "B", "A"])

    def test_diamond(self):
        """Общая зависимость загружается один раз и раньше всех."""
        text = "A: B C\nB: D\nC: D\nD:\n"
        order = self.order(text)
        self.assertEqual(order, ["D", "B", "C", "A"])
        self.assert_dependencies_first(text, order)

    def test_root_is_last(self):
        """Анализируемый пакет загружается последним."""
        text = "APP: CORE UI\nCORE: UTIL\nUI: CORE UTIL\nUTIL:\n"
        order = self.order(text, "APP")
        self.assertEqual(order[-1], "APP")
        self.assertEqual(len(order), len(set(order)))
        self.assert_dependencies_first(text, order)

    def test_single_package(self):
        """Пакет без зависимостей — порядок из одного пакета."""
        self.assertEqual(self.order("A:\n"), ["A"])

    def test_cycle_terminates(self):
        """Цикл не мешает построить порядок: все пакеты по одному разу."""
        order = self.order("A: B\nB: C\nC: A D\nD:\n")
        self.assertEqual(order, ["D", "C", "B", "A"])

    def test_self_dependency(self):
        """Зависимость от себя не приводит к повтору пакета."""
        self.assertEqual(self.order("A: A B\nB:\n"), ["B", "A"])

    def test_filtered_packages_absent(self):
        """Исключённые фильтром пакеты в порядок не попадают."""
        order = self.order("A: B XB\nB:\nXB: C\nC:\n", "A", "X")
        self.assertEqual(order, ["B", "A"])


if __name__ == "__main__":
    unittest.main()
