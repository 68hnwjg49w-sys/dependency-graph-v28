"""Получение прямых зависимостей пакета npm из репозитория по URL.

Используется HTTP API реестра npm: GET {repository}/{package} возвращает
JSON-документ пакета со списком версий. Готовые менеджеры пакетов и
сторонние библиотеки не используются — только urllib и json.
"""

import json
import urllib.error
import urllib.request
from urllib.parse import quote

from src.errors import RepositoryError

ACCEPT = "application/vnd.npm.install-v1+json"
USER_AGENT = "depgraph-v28"
TIMEOUT = 15
NOT_FOUND = 404
LATEST_TAG = "latest"


def package_url(repository, package):
    """Строит URL документа пакета; «/» в @scope/name кодируется."""
    return "{}/{}".format(repository.rstrip("/"), quote(package, safe="@"))


def fetch_document(url, opener=urllib.request.urlopen):
    """Загружает и разбирает JSON-документ пакета из репозитория."""
    request = urllib.request.Request(
        url, headers={"Accept": ACCEPT, "User-Agent": USER_AGENT}
    )
    try:
        with opener(request, timeout=TIMEOUT) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        raise RepositoryError(_http_problem(error, url)) from error
    except urllib.error.URLError as error:
        raise RepositoryError("не удалось подключиться к {}: {}".format(
            url, error.reason)) from error
    except (OSError, ValueError) as error:
        raise RepositoryError(
            "ошибка при загрузке {}: {}".format(url, error)
        ) from error
    return _parse_json(data, url)


def _http_problem(error, url):
    """Сообщение об ответе сервера с кодом ошибки."""
    if error.code == NOT_FOUND:
        return "пакет не найден в репозитории: {}".format(url)
    return "репозиторий вернул ошибку {} для {}".format(error.code, url)


def _parse_json(data, url):
    """Разбирает ответ репозитория как JSON-объект."""
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise RepositoryError(
            "ответ репозитория не является JSON: {}".format(url)
        ) from error
    if not isinstance(document, dict):
        raise RepositoryError(
            "неожиданный формат ответа репозитория: {}".format(url)
        )
    return document


def direct_dependencies(document, package):
    """Возвращает последнюю версию пакета и её прямые зависимости."""
    try:
        version = document["dist-tags"][LATEST_TAG]
        manifest = document["versions"][version]
    except (KeyError, TypeError) as error:
        raise RepositoryError(
            "в ответе репозитория нет последней версии пакета {}".format(
                package)
        ) from error
    dependencies = {}
    if isinstance(manifest, dict):
        dependencies = manifest.get("dependencies") or {}
    if not isinstance(dependencies, dict):
        raise RepositoryError(
            "неверный список зависимостей пакета {}".format(package)
        )
    return version, dict(dependencies)


def get_direct_dependencies(repository, package,
                            opener=urllib.request.urlopen):
    """Загружает документ пакета и извлекает его прямые зависимости."""
    document = fetch_document(package_url(repository, package), opener)
    return direct_dependencies(document, package)


class NpmRepository:
    """Источник зависимостей — реестр npm по URL (последние версии)."""

    def __init__(self, repository, opener=urllib.request.urlopen):
        """Запоминает адрес реестра и функцию загрузки."""
        self.repository = repository
        self.opener = opener
        self.versions = {}

    def dependencies(self, package):
        """Возвращает имена прямых зависимостей последней версии пакета."""
        version, dependencies = get_direct_dependencies(
            self.repository, package, self.opener)
        self.versions[package] = version
        return sorted(dependencies)
