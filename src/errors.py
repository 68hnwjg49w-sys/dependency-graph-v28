"""Исключения приложения, о которых нужно сообщить пользователю."""


class AppError(Exception):
    """Базовая ошибка приложения, понятная пользователю."""


class ConfigError(AppError):
    """Ошибки в конфигурационном файле: одна или несколько."""

    def __init__(self, messages):
        """Запоминает список сообщений об ошибках."""
        super().__init__("\n".join(messages))
        self.messages = list(messages)


class RepositoryError(AppError):
    """Ошибка получения данных о пакете из репозитория."""


class GraphError(AppError):
    """Ошибка построения графа зависимостей."""
