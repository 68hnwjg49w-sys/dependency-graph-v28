"""Модульные тесты точки входа."""

import io
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from src.main import EXIT_CONFIG_ERROR, EXIT_OK, EXIT_REPOSITORY_ERROR, main
from tests.helpers import FakeOpener, package_document

REGISTRY = "https://registry.npmjs.org"
CONFIG = """[settings]
package = {}
repository = https://registry.npmjs.org
output = g.svg
"""


class MainTest(unittest.TestCase):
    """Проверяет запуск приложения с конфигурационным файлом."""

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

    def test_prints_direct_dependencies(self):
        """Выводятся все прямые зависимости: имя и диапазон версий."""
        opener = FakeOpener({REGISTRY + "/express": package_document(
            "5.1.0", {"accepts": "^2.0.0", "debug": "^4.4.0"})})
        code, out, _ = self.run_main(CONFIG.format("express"), opener)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines(), [
            "Пакет: express 5.1.0",
            "Прямые зависимости (2):",
            "  accepts ^2.0.0",
            "  debug ^4.4.0",
        ])

    def test_parameters_are_not_printed(self):
        """Вывод параметров был только на этапе 1."""
        opener = FakeOpener({REGISTRY + "/lodash": package_document("4")})
        _, out, _ = self.run_main(CONFIG.format("lodash"), opener)
        self.assertNotIn("repository =", out)

    def test_no_dependencies(self):
        """У пакета без зависимостей выводится сообщение."""
        opener = FakeOpener({REGISTRY + "/lodash": package_document("4")})
        code, out, _ = self.run_main(CONFIG.format("lodash"), opener)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("Прямых зависимостей нет", out)

    def test_repository_error(self):
        """Ошибка репозитория печатается в поток ошибок, код 3."""
        code, out, err = self.run_main(CONFIG.format("nope"))
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка: пакет не найден", err)

    def test_network_error(self):
        """Недоступный сервер — ошибка подключения, код 3."""
        opener = FakeOpener(error=urllib.error.URLError("no host"))
        code, _, err = self.run_main(CONFIG.format("express"), opener)
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("не удалось подключиться", err)

    def test_test_mode_not_yet_supported(self):
        """Тестовый режим будет на этапе 3: понятная ошибка."""
        repo = self.base / "repo.txt"
        repo.write_text("A: B\n", encoding="utf-8")
        text = ("[settings]\npackage = A\nrepository = {}\n"
                "test_mode = true\noutput = g.svg\n").format(repo)
        code, _, err = self.run_main(text)
        self.assertEqual(code, EXIT_REPOSITORY_ERROR)
        self.assertIn("этапе 3", err)

    def test_config_errors_go_to_stderr(self):
        """Ошибки конфигурации печатаются в поток ошибок, код 1."""
        code, out, err = self.run_main("[settings]\n")
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка конфигурации:", err)
        self.assertIn("  - package: обязательный параметр не задан", err)


if __name__ == "__main__":
    unittest.main()
