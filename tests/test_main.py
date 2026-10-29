"""Модульные тесты точки входа."""

import io
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from src.main import EXIT_CONFIG_ERROR, EXIT_DATA_ERROR, EXIT_OK, main
from tests.helpers import FakeOpener, package_document

REGISTRY = "https://registry.npmjs.org"
NPM_CONFIG = """[settings]
package = {}
repository = https://registry.npmjs.org
output = g.svg
filter = {}
"""
TEST_CONFIG = """[settings]
package = {}
repository = {}
test_mode = true
output = g.svg
filter = {}
"""


class MainTestCase(unittest.TestCase):
    """Создаёт временный каталог и запускает main."""

    def setUp(self):
        """Создаёт временный каталог."""
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        """Удаляет временный каталог."""
        self._tmp.cleanup()

    def run_main(self, text, opener=None):
        """Пишет INI, запускает main и возвращает код, вывод и ошибки."""
        path = self.base / "config.ini"
        path.write_text(text, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--config", str(path)], opener or FakeOpener())
        return code, out.getvalue(), err.getvalue()

    def run_test_repo(self, text, package="A", name_filter=""):
        """Запускает main с тестовым репозиторием из текста."""
        repo = self.base / "repo.txt"
        repo.write_text(text, encoding="utf-8")
        return self.run_main(TEST_CONFIG.format(package, repo, name_filter))


class NpmGraphTest(MainTestCase):
    """Проверяет граф по реестру npm с подменёнными ответами."""

    def opener(self):
        """Реестр из трёх пакетов: app -> lib, util; lib -> util."""
        return FakeOpener({
            REGISTRY + "/app": package_document(
                "1.0.0", {"util": "^1", "lib": "^2"}),
            REGISTRY + "/lib": package_document("2.0.0", {"util": "^1"}),
            REGISTRY + "/util": package_document("1.5.0"),
        })

    def test_transitive_graph(self):
        """Выводятся транзитивные зависимости, каждый пакет один раз."""
        opener = self.opener()
        code, out, _ = self.run_main(NPM_CONFIG.format("app", ""), opener)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines(), [
            "Граф зависимостей пакета app (обход в глубину):",
            "  app -> lib, util",
            "  lib -> util",
            "  util -> нет зависимостей",
            "Пакетов в графе: 3",
            "Циклических зависимостей нет",
        ])
        self.assertEqual(len(opener.requests), 3)

    def test_filter(self):
        """Пакеты с подстрокой фильтра не запрашиваются."""
        opener = self.opener()
        _, out, _ = self.run_main(NPM_CONFIG.format("app", "util"), opener)
        self.assertIn("  lib -> нет зависимостей", out)
        self.assertIn("Исключены фильтром 'util': util", out)
        self.assertEqual(len(opener.requests), 2)

    def test_missing_dependency(self):
        """Зависимость не найдена в реестре — ошибка, код 3."""
        opener = FakeOpener({REGISTRY + "/app": package_document(
            "1.0.0", {"ghost": "^1"})})
        code, out, err = self.run_main(NPM_CONFIG.format("app", ""), opener)
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка: пакет не найден", err)

    def test_network_error(self):
        """Недоступный сервер — ошибка подключения, код 3."""
        opener = FakeOpener(error=urllib.error.URLError("no host"))
        code, _, err = self.run_main(NPM_CONFIG.format("app", ""), opener)
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("не удалось подключиться", err)


class TestModeTest(MainTestCase):
    """Проверяет режим тестового репозитория."""

    def test_cycle_is_reported(self):
        """Цикл выводится отдельной строкой."""
        code, out, _ = self.run_test_repo("A: B\nB: A\n")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("  B -> A", out)
        self.assertIn("Циклические зависимости (1):\n  A -> B -> A", out)

    def test_filter_in_test_mode(self):
        """Фильтр работает и в тестовом режиме."""
        _, out, _ = self.run_test_repo("A: XB C\nXB:\nC:\n", "A", "X")
        self.assertIn("  A -> C", out)
        self.assertIn("Исключены фильтром 'X': XB", out)

    def test_repository_file_errors(self):
        """Ошибки файла тестового репозитория — код 3."""
        code, _, err = self.run_test_repo("A: b\n")
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("строка 1", err)

    def test_root_filtered(self):
        """Корень с подстрокой фильтра — ошибка, код 3."""
        code, _, err = self.run_test_repo("XA:\n", "XA", "X")
        self.assertEqual(code, EXIT_DATA_ERROR)
        self.assertIn("подстроку фильтра", err)


class ConfigErrorTest(MainTestCase):
    """Проверяет ошибки конфигурации."""

    def test_config_errors_go_to_stderr(self):
        """Ошибки конфигурации печатаются в поток ошибок, код 1."""
        code, out, err = self.run_main("[settings]\n")
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка конфигурации:", err)
        self.assertIn("  - package: обязательный параметр не задан", err)


if __name__ == "__main__":
    unittest.main()
