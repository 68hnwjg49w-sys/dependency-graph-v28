"""Модульные тесты файла тестового репозитория."""

import tempfile
import unittest
from pathlib import Path

from src.errors import RepositoryError
from src.testrepo import FileRepository, parse_repository


class ParseTest(unittest.TestCase):
    """Проверяет разбор текста тестового репозитория."""

    def test_packages_and_dependencies(self):
        """Строки «ПАКЕТ: ЗАВИСИМОСТИ» превращаются в словарь."""
        packages = parse_repository("A: B C\nB:\nC:\n")
        self.assertEqual(packages, {"A": ["B", "C"], "B": [], "C": []})

    def test_comments_spaces_and_long_names(self):
        """Комментарии, пустые строки и лишние пробелы пропускаются."""
        packages = parse_repository(
            "# граф\n\n  APP :  CORE   UI \nCORE:\nUI:\n")
        self.assertEqual(packages["APP"], ["CORE", "UI"])

    def test_repeated_dependency(self):
        """Повтор зависимости в строке учитывается один раз."""
        self.assertEqual(parse_repository("A: B B\nB:\n")["A"], ["B"])

    def test_all_errors_reported(self):
        """Все ошибки формата выводятся вместе с номерами строк."""
        with self.assertRaises(RepositoryError) as caught:
            parse_repository("A: B\nB C\nc: D\nD: e\nA: D\n")
        message = str(caught.exception)
        for part in ("строка 2", "строка 3", "строка 4",
                     "строка 5: пакет A описан повторно"):
            self.assertIn(part, message)

    def test_empty(self):
        """Файл без пакетов — ошибка."""
        with self.assertRaisesRegex(RepositoryError, "пуст"):
            parse_repository("# только комментарий\n\n")

    def test_lowercase_and_digits_rejected(self):
        """Имена только из больших латинских букв."""
        for text in ("a: B\n", "A1: B\n", "A: B2\n", "Ä: B\n"):
            with self.assertRaises(RepositoryError):
                parse_repository(text)


class FileRepositoryTest(unittest.TestCase):
    """Проверяет чтение файла и выдачу зависимостей."""

    def test_load_and_dependencies(self):
        """Файл читается, зависимости выдаются копией списка."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "repo.txt"
            path.write_text("A: B\nB:\n", encoding="utf-8")
            repository = FileRepository.load(str(path))
        dependencies = repository.dependencies("A")
        dependencies.append("Z")
        self.assertEqual(repository.dependencies("A"), ["B"])

    def test_unknown_package(self):
        """Пакета нет в файле — ошибка."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            FileRepository({"A": []}).dependencies("B")

    def test_unreadable_file(self):
        """Файл не прочитать — ошибка."""
        with self.assertRaisesRegex(RepositoryError, "не удалось прочитать"):
            FileRepository.load("no/such/file.txt")


if __name__ == "__main__":
    unittest.main()
