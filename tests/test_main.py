"""Модульные тесты точки входа."""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from src.main import EXIT_CONFIG_ERROR, EXIT_OK, main


class MainTest(unittest.TestCase):
    """Проверяет запуск приложения с конфигурационным файлом."""

    def setUp(self):
        """Создаёт временный каталог."""
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        """Удаляет временный каталог."""
        self._tmp.cleanup()

    def run_main(self, text):
        """Пишет INI, запускает main и возвращает код, вывод и ошибки."""
        path = self.base / "config.ini"
        path.write_text(text, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--config", str(path)])
        return code, out.getvalue(), err.getvalue()

    def test_prints_parameters(self):
        """При запуске выводятся все параметры: ключ = значение."""
        code, out, _ = self.run_main(
            "[settings]\npackage = express\n"
            "repository = https://registry.npmjs.org\noutput = g.svg\n"
        )
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(out.splitlines(), [
            "package = express",
            "repository = https://registry.npmjs.org",
            "test_mode = false",
            "output = g.svg",
            "filter =",
        ])

    def test_errors_go_to_stderr(self):
        """Ошибки печатаются в поток ошибок, код завершения 1."""
        code, out, err = self.run_main("[settings]\n")
        self.assertEqual(code, EXIT_CONFIG_ERROR)
        self.assertEqual(out, "")
        self.assertIn("ошибка конфигурации:", err)
        self.assertIn("  - package: обязательный параметр не задан", err)


if __name__ == "__main__":
    unittest.main()
