"""Помощники для тестов: поддельный HTTP-ответ и документы пакетов."""

import io
import json
import urllib.error


class FakeResponse(io.BytesIO):
    """Ответ сервера: байты тела, работает как контекстный менеджер."""


class FakeOpener:
    """Заменяет urlopen: отдаёт заданные ответы и запоминает запросы."""

    def __init__(self, documents=None, error=None):
        """Запоминает документы по URL или исключение для любого запроса."""
        self.documents = documents or {}
        self.error = error
        self.requests = []

    def __call__(self, request, timeout=None):
        """Возвращает ответ для URL запроса или выбрасывает ошибку."""
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        body = self.documents.get(request.full_url)
        if body is None:
            raise urllib.error.HTTPError(
                request.full_url, 404, "Not Found", None, None)
        if not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        return FakeResponse(body)


def package_document(version, dependencies=None):
    """Строит документ пакета в формате реестра npm."""
    manifest = {"name": "pkg", "version": version}
    if dependencies is not None:
        manifest["dependencies"] = dependencies
    return {
        "name": "pkg",
        "dist-tags": {"latest": version},
        "versions": {"0.0.1": {"version": "0.0.1"}, version: manifest},
    }
