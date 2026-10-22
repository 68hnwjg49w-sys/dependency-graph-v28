"""Чтение и проверка конфигурационного файла формата INI."""

import configparser
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from src.errors import ConfigError

SECTION = "settings"
KEYS = ("package", "repository", "test_mode", "output", "filter")
REQUIRED_KEYS = ("package", "repository", "output")
DEFAULTS = {"test_mode": "false", "filter": ""}
BOOLEANS = configparser.ConfigParser.BOOLEAN_STATES
MAX_NAME_LENGTH = 214
NAME_PATTERN = re.compile(
    r"^(@[a-z0-9~-][a-z0-9._~-]*/)?[a-z0-9~-][a-z0-9._~-]*$"
)
TEST_NAME_PATTERN = re.compile(r"^[A-Z]+$")
URL_SCHEMES = ("http", "https")
IMAGE_SUFFIX = ".svg"


@dataclass(frozen=True)
class Config:
    """Параметры, настраиваемые пользователем."""

    package: str
    repository: str
    test_mode: bool
    output: str
    name_filter: str

    def items(self):
        """Возвращает пары «ключ — значение» в порядке файла INI."""
        mode = "true" if self.test_mode else "false"
        return [
            ("package", self.package),
            ("repository", self.repository),
            ("test_mode", mode),
            ("output", self.output),
            ("filter", self.name_filter),
        ]


def load_config(path):
    """Читает INI-файл, проверяет все параметры и возвращает Config."""
    values, errors = _read_section(path)
    errors += _key_errors(values)
    errors += _value_errors(values)
    if errors:
        raise ConfigError(errors)
    return Config(
        package=values["package"],
        repository=values["repository"],
        test_mode=BOOLEANS[values["test_mode"].lower()],
        output=values["output"],
        name_filter=values["filter"],
    )


def _read_section(path):
    """Читает секцию [settings]; возвращает значения и ошибки секций."""
    parser = configparser.ConfigParser(
        interpolation=None, default_section="__defaults__"
    )
    try:
        with open(_check_path(path), encoding="utf-8") as stream:
            parser.read_file(stream)
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigError(
            ["не удалось прочитать файл {}: {}".format(path, error)]
        ) from error
    except configparser.Error as error:
        raise ConfigError(
            ["ошибка формата INI: {}".format(_ini_problem(error))]
        ) from error
    if not parser.has_section(SECTION):
        raise ConfigError(["нет секции [{}]".format(SECTION)])
    errors = [
        "неизвестная секция [{}]".format(name)
        for name in parser.sections() if name != SECTION
    ]
    return dict(parser.items(SECTION)), errors


def _ini_problem(error):
    """Переводит ошибку разбора INI в понятное сообщение."""
    if isinstance(error, configparser.MissingSectionHeaderError):
        return "строка {}: параметры должны идти после заголовка " \
               "секции [{}]".format(error.lineno, SECTION)
    if isinstance(error, configparser.ParsingError):
        return "строка {}: ожидается запись «ключ = значение»".format(
            error.errors[0][0])
    if isinstance(error, configparser.DuplicateOptionError):
        return "параметр '{}' задан дважды".format(error.option)
    if isinstance(error, configparser.DuplicateSectionError):
        return "секция [{}] задана дважды".format(error.section)
    return str(error).splitlines()[0]


def _check_path(path):
    """Проверяет путь к файлу конфигурации и возвращает его."""
    if not path:
        raise ConfigError(["путь к файлу конфигурации пуст"])
    file = Path(path)
    if not file.exists():
        raise ConfigError(["файл конфигурации не найден: {}".format(path)])
    if not file.is_file():
        raise ConfigError(["{}: указан не файл".format(path)])
    return file


def _key_errors(values):
    """Ищет неизвестные и пропущенные параметры, дописывает умолчания."""
    errors = [
        "неизвестный параметр '{}'".format(key)
        for key in values if key not in KEYS
    ]
    for key in REQUIRED_KEYS:
        if key not in values:
            errors.append("{}: обязательный параметр не задан".format(key))
    for key, default in DEFAULTS.items():
        values.setdefault(key, default)
    return errors


def _value_errors(values):
    """Проверяет значения всех заданных параметров."""
    errors = []
    for key, check in CHECKS.items():
        if key in values:
            problem = check(values[key], values)
            if problem:
                errors.append("{}: {}".format(key, problem))
    return errors


def _test_mode(values):
    """Режим тестового репозитория: True, False или None, если неверен."""
    return BOOLEANS.get(values["test_mode"].lower())


def _check_package(value, values):
    """Проверяет имя пакета: npm или большие латинские буквы в тесте."""
    if not value:
        return "не задано имя пакета"
    if _test_mode(values):
        if not TEST_NAME_PATTERN.match(value):
            return "в тестовом репозитории пакеты называются большими " \
                   "латинскими буквами, получено '{}'".format(value)
        return None
    if len(value) > MAX_NAME_LENGTH:
        return "имя длиннее {} символов".format(MAX_NAME_LENGTH)
    if not NAME_PATTERN.match(value):
        return "недопустимое имя пакета npm: '{}'".format(value)
    return None


def _check_test_mode(value, _values):
    """Проверяет режим работы с тестовым репозиторием."""
    if value.lower() not in BOOLEANS:
        return "ожидается true или false, получено '{}'".format(value)
    return None


def _check_repository(value, values):
    """Проверяет URL репозитория или путь к файлу тестового репозитория."""
    if not value:
        return "не задан URL репозитория или путь к файлу"
    mode = _test_mode(values)
    if mode is None:
        return None
    if mode:
        return _check_test_file(value)
    return _check_url(value)


def _check_url(value):
    """Проверяет, что значение — адрес http:// или https://."""
    parsed = urlparse(value)
    if parsed.scheme not in URL_SCHEMES or not parsed.netloc:
        return "ожидается URL вида https://registry.npmjs.org, " \
               "получено '{}'".format(value)
    return None


def _check_test_file(value):
    """Проверяет путь к файлу тестового репозитория."""
    file = Path(value)
    if not file.exists():
        return "файл тестового репозитория не найден: {}".format(value)
    if not file.is_file():
        return "{}: указан не файл".format(value)
    return None


def _check_output(value, _values):
    """Проверяет имя файла для изображения графа."""
    if not value:
        return "не задано имя файла с изображением"
    file = Path(value)
    if file.suffix.lower() != IMAGE_SUFFIX:
        return "имя файла должно оканчиваться на {}: '{}'".format(
            IMAGE_SUFFIX, value)
    if file.is_dir():
        return "{}: это каталог, а не файл".format(value)
    if not file.parent.is_dir():
        return "каталог для файла не существует: {}".format(file.parent)
    return None


def _check_filter(value, _values):
    """Проверяет подстроку для фильтрации пакетов."""
    if any(char.isspace() for char in value):
        return "подстрока не должна содержать пробелов: '{}'".format(value)
    return None


CHECKS = {
    "package": _check_package,
    "test_mode": _check_test_mode,
    "repository": _check_repository,
    "output": _check_output,
    "filter": _check_filter,
}
