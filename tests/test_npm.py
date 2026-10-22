"""Модульные тесты получения прямых зависимостей из реестра npm."""

import socket
import unittest
import urllib.error

from src.errors import RepositoryError
from src.npm import (
    ACCEPT,
    direct_dependencies,
    fetch_document,
    get_direct_dependencies,
    package_url,
)
from tests.helpers import FakeOpener, package_document

REGISTRY = "https://registry.npmjs.org"


class PackageUrlTest(unittest.TestCase):
    """Проверяет построение URL документа пакета."""

    def test_simple_name(self):
        """Обычное имя дописывается к адресу репозитория."""
        self.assertEqual(package_url(REGISTRY, "express"),
                         REGISTRY + "/express")

    def test_trailing_slash(self):
        """Лишний «/» в конце адреса репозитория не дублируется."""
        self.assertEqual(package_url(REGISTRY + "/", "express"),
                         REGISTRY + "/express")

    def test_scoped_name(self):
        """В имени со scope «/» кодируется как %2F, «@» остаётся."""
        self.assertEqual(package_url(REGISTRY, "@babel/core"),
                         REGISTRY + "/@babel%2Fcore")


class DirectDependenciesTest(unittest.TestCase):
    """Проверяет извлечение зависимостей из документа пакета."""

    def test_latest_version_dependencies(self):
        """Берутся зависимости версии из dist-tags.latest."""
        document = package_document("2.0.0", {"a": "^1.0.0", "b": "~2.1"})
        self.assertEqual(direct_dependencies(document, "pkg"),
                         ("2.0.0", {"a": "^1.0.0", "b": "~2.1"}))

    def test_no_dependencies(self):
        """Нет поля dependencies — пустой словарь."""
        document = package_document("1.0.0")
        self.assertEqual(direct_dependencies(document, "pkg"),
                         ("1.0.0", {}))

    def test_missing_latest(self):
        """Нет dist-tags или нужной версии — ошибка."""
        for document in ({}, {"dist-tags": {}},
                         {"dist-tags": {"latest": "1"}, "versions": {}},
                         {"dist-tags": None}):
            with self.assertRaisesRegex(RepositoryError, "последней версии"):
                direct_dependencies(document, "pkg")

    def test_bad_dependencies(self):
        """Поле dependencies не словарь — ошибка."""
        document = package_document("1.0.0", ["a", "b"])
        with self.assertRaisesRegex(RepositoryError, "список зависимостей"):
            direct_dependencies(document, "pkg")


class FetchTest(unittest.TestCase):
    """Проверяет загрузку документа и ошибки сети."""

    def test_request_headers(self):
        """Запрос идёт с заголовками Accept и User-Agent."""
        opener = FakeOpener({REGISTRY + "/a": package_document("1.0.0")})
        fetch_document(REGISTRY + "/a", opener)
        request = opener.requests[0]
        self.assertEqual(request.get_header("Accept"), ACCEPT)
        self.assertTrue(request.get_header("User-agent"))

    def test_not_found(self):
        """Ответ 404 — пакет не найден."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            fetch_document(REGISTRY + "/nope", FakeOpener())

    def test_other_http_error(self):
        """Другие коды ответа — ошибка с кодом."""
        error = urllib.error.HTTPError(REGISTRY, 500, "err", None, None)
        with self.assertRaisesRegex(RepositoryError, "ошибку 500"):
            fetch_document(REGISTRY + "/a", FakeOpener(error=error))

    def test_connection_error(self):
        """Сервер недоступен — ошибка подключения."""
        error = urllib.error.URLError("Name or service not known")
        with self.assertRaisesRegex(RepositoryError, "не удалось подключ"):
            fetch_document(REGISTRY + "/a", FakeOpener(error=error))

    def test_timeout(self):
        """Истекло время ожидания — ошибка загрузки."""
        error = socket.timeout("timed out")
        with self.assertRaisesRegex(RepositoryError, "ошибка при загрузке"):
            fetch_document(REGISTRY + "/a", FakeOpener(error=error))

    def test_not_json(self):
        """Ответ не JSON или не объект — ошибка."""
        for body in (b"<html>", b"\xff\xfe", b"[1, 2]"):
            opener = FakeOpener({REGISTRY + "/a": body})
            with self.assertRaises(RepositoryError):
                fetch_document(REGISTRY + "/a", opener)


class GetDirectDependenciesTest(unittest.TestCase):
    """Проверяет получение зависимостей целиком."""

    def test_scoped_package(self):
        """Пакет со scope запрашивается по закодированному URL."""
        opener = FakeOpener({
            REGISTRY + "/@babel%2Fcore": package_document(
                "7.0.0", {"@babel/parser": "^7.0.0"}),
        })
        version, dependencies = get_direct_dependencies(
            REGISTRY, "@babel/core", opener)
        self.assertEqual(version, "7.0.0")
        self.assertEqual(dependencies, {"@babel/parser": "^7.0.0"})


if __name__ == "__main__":
    unittest.main()
