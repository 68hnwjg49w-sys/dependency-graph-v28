"""Модульные тесты чтения и проверки конфигурационного файла."""

import tempfile
import unittest
from pathlib import Path

from src.config import load_config
from src.errors import ConfigError

VALID = """[settings]
package = express
repository = https://registry.npmjs.org
test_mode = false
output = graph.svg
filter = debug
"""


class ConfigTestCase(unittest.TestCase):
    """Создаёт временный каталог для файлов INI."""

    def setUp(self):
        """Создаёт временный каталог."""
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        """Удаляет временный каталог."""
        self._tmp.cleanup()

    def write(self, text, name="config.ini"):
        """Записывает файл INI и возвращает путь к нему."""
        path = self.base / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def errors(self, text):
        """Возвращает список ошибок для заданного содержимого INI."""
        with self.assertRaises(ConfigError) as caught:
            load_config(self.write(text))
        return caught.exception.messages

    def settings(self, **changes):
        """Собирает секцию [settings], заменяя или убирая параметры."""
        values = {
            "package": "express",
            "repository": "https://registry.npmjs.org",
            "test_mode": "false",
            "output": "graph.svg",
            "filter": "",
        }
        values.update(changes)
        lines = ["[settings]"] + [
            "{} = {}".format(key, value)
            for key, value in values.items() if value is not None
        ]
        return "\n".join(lines) + "\n"


class ValidConfigTest(ConfigTestCase):
    """Проверяет чтение правильного файла."""

    def test_all_parameters(self):
        """Все пять параметров читаются из файла."""
        config = load_config(self.write(VALID))
        self.assertEqual(config.package, "express")
        self.assertEqual(config.repository, "https://registry.npmjs.org")
        self.assertFalse(config.test_mode)
        self.assertEqual(config.output, "graph.svg")
        self.assertEqual(config.name_filter, "debug")

    def test_items_in_file_order(self):
        """Пары ключ — значение выводятся в порядке файла."""
        config = load_config(self.write(VALID))
        self.assertEqual(config.items(), [
            ("package", "express"),
            ("repository", "https://registry.npmjs.org"),
            ("test_mode", "false"),
            ("output", "graph.svg"),
            ("filter", "debug"),
        ])

    def test_optional_parameters_have_defaults(self):
        """Без test_mode и filter действуют значения по умолчанию."""
        text = self.settings(test_mode=None, filter=None)
        config = load_config(self.write(text))
        self.assertFalse(config.test_mode)
        self.assertEqual(config.name_filter, "")

    def test_scoped_package(self):
        """Имя пакета со scope (@babel/core) допустимо."""
        text = self.settings(package="@babel/core")
        self.assertEqual(load_config(self.write(text)).package, "@babel/core")

    def test_boolean_spellings(self):
        """Режим можно задать как yes/no, on/off, 1/0."""
        for value in ("no", "off", "0", "FALSE"):
            text = self.settings(test_mode=value)
            self.assertFalse(load_config(self.write(text)).test_mode)

    def test_test_mode_with_file(self):
        """В тестовом режиме repository — путь к существующему файлу."""
        repo = self.write("A: B\n", "repo.txt")
        text = self.settings(package="A", repository=repo, test_mode="true")
        config = load_config(self.write(text))
        self.assertTrue(config.test_mode)
        self.assertEqual(config.repository, repo)

    def test_output_in_existing_directory(self):
        """Файл изображения можно положить в существующий каталог."""
        output = str(self.base / "graph.SVG")
        text = self.settings(output=output)
        self.assertEqual(load_config(self.write(text)).output, output)


class FileErrorsTest(ConfigTestCase):
    """Проверяет ошибки, связанные с самим файлом."""

    def test_missing_file(self):
        """Несуществующий файл — ошибка."""
        with self.assertRaisesRegex(ConfigError, "не найден"):
            load_config(str(self.base / "nope.ini"))

    def test_directory_instead_of_file(self):
        """Каталог вместо файла — ошибка."""
        with self.assertRaisesRegex(ConfigError, "указан не файл"):
            load_config(str(self.base))

    def test_empty_path(self):
        """Пустой путь — ошибка."""
        with self.assertRaisesRegex(ConfigError, "пуст"):
            load_config("")

    def test_not_utf8(self):
        """Файл не в кодировке UTF-8 — ошибка чтения."""
        path = self.base / "bad.ini"
        path.write_bytes(b"[settings]\npackage = \xff\xfe\n")
        with self.assertRaisesRegex(ConfigError, "не удалось прочитать"):
            load_config(str(path))


class FormatErrorsTest(ConfigTestCase):
    """Проверяет ошибки формата INI и структуры секций."""

    def test_no_section_header(self):
        """Параметры без заголовка секции — ошибка с номером строки."""
        self.assertIn("строка 1", self.errors("package = express\n")[0])

    def test_line_without_equals(self):
        """Строка без «=» — ошибка с номером строки."""
        messages = self.errors("[settings]\npackage express\n")
        self.assertIn("строка 2", messages[0])

    def test_duplicate_key(self):
        """Повтор параметра — ошибка."""
        text = VALID + "package = react\n"
        self.assertIn("задан дважды", self.errors(text)[0])

    def test_duplicate_section(self):
        """Повтор секции — ошибка."""
        text = VALID + "[settings]\n"
        self.assertIn("секция [settings] задана дважды", self.errors(text)[0])

    def test_missing_settings_section(self):
        """Нет секции [settings] — ошибка."""
        messages = self.errors("[options]\npackage = express\n")
        self.assertEqual(messages, ["нет секции [settings]"])

    def test_unknown_section_and_key(self):
        """Лишние секции и параметры — ошибки."""
        text = VALID + "color = red\n[extra]\nsize = 1\n"
        self.assertEqual(self.errors(text), [
            "неизвестная секция [extra]",
            "неизвестный параметр 'color'",
        ])

    def test_missing_required_keys(self):
        """Пропущенные обязательные параметры перечисляются все."""
        messages = self.errors("[settings]\ntest_mode = false\n")
        self.assertEqual(messages, [
            "package: обязательный параметр не задан",
            "repository: обязательный параметр не задан",
            "output: обязательный параметр не задан",
        ])


class ValueErrorsTest(ConfigTestCase):
    """Проверяет ошибки значений каждого параметра."""

    def assert_error(self, text, expected):
        """Проверяет, что среди ошибок есть ожидаемое сообщение."""
        messages = self.errors(text)
        self.assertTrue(
            any(expected in message for message in messages), messages
        )

    def test_package_errors(self):
        """Имя пакета: пустое, недопустимое, слишком длинное."""
        self.assert_error(self.settings(package=""), "не задано имя")
        self.assert_error(self.settings(package="My App"), "недопустимое")
        self.assert_error(self.settings(package=".hidden"), "недопустимое")
        self.assert_error(self.settings(package="a" * 215), "длиннее 214")

    def test_test_package_must_be_capital_letters(self):
        """В тестовом режиме пакет — большие латинские буквы."""
        repo = self.write("A: B\n", "repo.txt")
        text = self.settings(package="a", repository=repo, test_mode="true")
        self.assert_error(text, "большими латинскими буквами")

    def test_repository_errors(self):
        """URL: пустой, без схемы, не http/https, без адреса сервера."""
        self.assert_error(self.settings(repository=""), "не задан URL")
        for url in ("registry.npmjs.org", "ftp://host", "https://"):
            self.assert_error(self.settings(repository=url), "ожидается URL")

    def test_test_repository_errors(self):
        """Тестовый режим: файла нет или указан каталог."""
        missing = str(self.base / "nope.txt")
        text = self.settings(package="A", repository=missing,
                             test_mode="true")
        self.assert_error(text, "не найден")
        text = self.settings(package="A", repository=str(self.base),
                             test_mode="true")
        self.assert_error(text, "указан не файл")

    def test_test_mode_error(self):
        """Режим не true/false — ошибка, repository не проверяется."""
        messages = self.errors(self.settings(test_mode="maybe"))
        self.assertEqual(messages, [
            "test_mode: ожидается true или false, получено 'maybe'"
        ])

    def test_output_errors(self):
        """Изображение: пусто, не .svg, каталог, нет каталога."""
        self.assert_error(self.settings(output=""), "не задано имя файла")
        self.assert_error(self.settings(output="graph.png"), ".svg")
        self.assert_error(self.settings(output=".svg"), ".svg")
        folder = self.base / "pic.svg"
        folder.mkdir()
        self.assert_error(self.settings(output=str(folder)), "это каталог")
        self.assert_error(self.settings(output="no_dir/graph.svg"),
                          "каталог для файла не существует")

    def test_filter_error(self):
        """Подстрока с пробелом — ошибка."""
        self.assert_error(self.settings(filter="a b"), "пробелов")

    def test_all_errors_reported_together(self):
        """Ошибки разных параметров выводятся вместе."""
        text = self.settings(package="Bad", test_mode="x",
                             output="g.png", filter="a b")
        self.assertEqual(len(self.errors(text)), 4)


if __name__ == "__main__":
    unittest.main()
