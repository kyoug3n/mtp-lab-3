"""Повыш. 5 и Повыш. 9: сериализация объектов в JSON.

:class:`Serializable` — абстрактный класс-контракт: объект, который умеет
отдать свои поля (:meth:`~Serializable.to_dict`) и создаться из них
(:meth:`~Serializable.from_dict`). :class:`JsonSerializer` ничего не знает о
фигурах: он записывает в JSON любые зарегистрированные классы-наследники
``Serializable`` и восстанавливает их обратно.

Объект записывается JSON-объектом с полем ``"type"`` — именем класса — и
полями из ``to_dict()``. Вложенные объекты и списки обрабатываются
рекурсивно, например чертёж с фигурами::

    {"type": "Drawing", "shapes": [{"type": "Circle", "radius": 2}]}

При чтении проверяется всё, что может быть не так с файлом: синтаксис JSON,
неизвестный тип, отсутствующие и лишние поля, повторяющиеся ключи, ``NaN``
и ``Infinity`` (модуль ``json`` по умолчанию их принимает, хотя стандарт
JSON их не знает), и значения — их проверяют конструкторы классов. Любая
такая ошибка — это :class:`SerializationError` с указанием места.
"""
import inspect
import json
import math
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import Any

TYPE_KEY = "type"


class SerializationError(ValueError):
    """Объект нельзя записать в JSON или восстановить из JSON."""


class Serializable(ABC):
    """Объект, который можно записать в JSON через :class:`JsonSerializer`."""

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Поля объекта.

        Значения — ``None``, ``bool``, числа, строки, списки и объекты
        ``Serializable``. Поле ``"type"`` занято сериализатором.
        """

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any]) -> "Serializable":
        """Создать объект из полей, которые вернул :meth:`to_dict`.

        Вложенные объекты к этому моменту уже восстановлены. Метод классовый:
        объекта ещё нет, его только предстоит создать, а класс нужен, чтобы
        наследник создавал объект своего класса.

        :raises TypeError, ValueError: если поля не подходят.
        """

    @staticmethod
    def check_fields(data: dict[str, Any], names: Iterable[str]) -> None:
        """Проверить, что в ``data`` ровно поля ``names``.

        :raises ValueError: если какого-то поля нет или есть лишнее.
        """
        expected = list(names)
        missing = [name for name in expected if name not in data]
        if missing:
            word = "поля" if len(missing) == 1 else "полей"
            raise ValueError(f"нет {word} {_quoted(missing)}")
        extra = [name for name in data if name not in expected]
        if extra:
            word = "лишнее поле" if len(extra) == 1 else "лишние поля"
            raise ValueError(f"{word} {_quoted(extra)}")


def _quoted(names: list[str]) -> str:
    return ", ".join(f"«{name}»" for name in names)


def _reject_constant(name: str) -> float:
    raise SerializationError(f"{name} — не число: в JSON нет такой константы")


def _parse_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise SerializationError(f"Число {text} больше 1e308 и не помещается "
                                 "во float")
    return value


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in pairs:
        if key in data:
            raise SerializationError(f"Поле «{key}» повторяется в объекте")
        data[key] = value
    return data


def _child(path: str, key: str | int) -> str:
    """Путь к вложенному значению: ``shapes[1].radius``."""
    if isinstance(key, int):
        return f"{path}[{key}]"
    return f"{path}.{key}" if path else key


def _error(path: str, message: str) -> SerializationError:
    if path:
        return SerializationError(f"{path}: {message}")
    return SerializationError(message[0].upper() + message[1:])


class JsonSerializer:
    """Запись объектов ``Serializable`` в JSON и чтение их обратно.

    Восстановить можно только объекты зарегистрированных классов: класс
    выбирается по полю ``"type"``, и произвольное имя из файла не должно
    создавать произвольные объекты.

    >>> from shapelab.shapes import Circle
    >>> serializer = JsonSerializer([Circle])
    >>> text = serializer.dumps(Circle(2))
    >>> print(text)
    {
      "type": "Circle",
      "radius": 2
    }
    >>> serializer.loads(text) == Circle(2)
    True
    >>> try:
    ...     serializer.loads('{"type": "Circle", "radius": -1}')
    ... except SerializationError as error:
    ...     print(error)
    Circle: Радиус: нужно число больше нуля, получено -1
    """

    def __init__(self, classes: Iterable[type[Serializable]] = ()) -> None:
        self._classes: dict[str, type[Serializable]] = {}
        for cls in classes:
            self.register(cls)

    def register(self, cls: type[Serializable]) -> type[Serializable]:
        """Разрешить запись и чтение объектов класса ``cls``.

        Возвращает сам класс, поэтому метод можно применять декоратором.

        :raises TypeError: если ``cls`` не наследник ``Serializable`` или
            абстрактный класс.
        :raises ValueError: если другой класс с таким именем уже
            зарегистрирован.
        """
        if not (isinstance(cls, type) and issubclass(cls, Serializable)):
            raise TypeError(f"{cls!r} не наследник Serializable")
        if inspect.isabstract(cls):
            raise TypeError(f"{cls.__name__} — абстрактный класс, "
                            "его объекты не создаются")
        name = cls.__name__
        if self._classes.get(name, cls) is not cls:
            raise ValueError(f"Класс с именем {name} уже зарегистрирован")
        self._classes[name] = cls
        return cls

    def to_data(self, value: object, path: str = "") -> Any:
        """Перевести значение в данные для ``json``: словари, списки, числа.

        :raises SerializationError: если значение нельзя записать в JSON.
        """
        if isinstance(value, Serializable):
            return self._object_to_data(value, path)
        if isinstance(value, (list, tuple)):
            return [self.to_data(item, _child(path, index))
                    for index, item in enumerate(value)]
        if isinstance(value, float) and not math.isfinite(value):
            raise _error(path, f"число {value} не записывается в JSON")
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        raise _error(path, f"значение типа {type(value).__name__} не "
                           "записывается в JSON")

    def _object_to_data(self, value: Serializable, path: str) -> Any:
        name = type(value).__name__
        if self._classes.get(name) is not type(value):
            raise _error(path, f"класс {name} не зарегистрирован")
        data: dict[str, Any] = {TYPE_KEY: name}
        for key, item in value.to_dict().items():
            if key == TYPE_KEY:
                raise _error(path, f"поле «{TYPE_KEY}» занято сериализатором")
            data[key] = self.to_data(item, _child(path, key))
        return data

    def from_data(self, data: Any, path: str = "") -> Any:
        """Восстановить объекты из данных, прочитанных ``json``.

        :raises SerializationError: если данные не описывают объект.
        """
        if isinstance(data, list):
            return [self.from_data(item, _child(path, index))
                    for index, item in enumerate(data)]
        if not isinstance(data, dict):
            return data
        name = data.get(TYPE_KEY)
        if not isinstance(name, str):
            raise _error(path, f"у объекта нет поля «{TYPE_KEY}» с именем "
                               "класса")
        cls = self._classes.get(name)
        if cls is None:
            raise _error(path, f"неизвестный тип «{name}»")
        fields = {
            key: self.from_data(value, _child(path, key))
            for key, value in data.items() if key != TYPE_KEY
        }
        try:
            return cls.from_dict(fields)
        except (TypeError, ValueError) as error:
            where = f"{path} ({name})" if path else name
            raise SerializationError(f"{where}: {error}") from error

    def dumps(self, obj: object) -> str:
        """Записать объект в JSON-строку (с отступами, кириллица как есть).

        :raises SerializationError: если объект нельзя записать в JSON.
        """
        data = self.to_data(obj)
        try:
            return json.dumps(data, ensure_ascii=False, indent=2,
                              allow_nan=False)
        except ValueError as error:  # например, целое длиннее 4300 цифр
            raise SerializationError(str(error)) from error

    def loads(self, text: str, expected: type | None = None) -> Any:
        """Прочитать объект из JSON-строки.

        :param expected: если задан, объект должен быть этого класса.
        :raises SerializationError: если текст не JSON или не описывает
            объект нужного класса.
        """
        try:
            data = json.loads(
                text,
                parse_constant=_reject_constant,
                parse_float=_parse_float,
                object_pairs_hook=_unique_keys,
            )
            result = self.from_data(data)
        except json.JSONDecodeError as error:
            raise SerializationError(
                f"Некорректный JSON: {error.msg} "
                f"(строка {error.lineno}, столбец {error.colno})"
            ) from error
        except SerializationError:
            raise
        except ValueError as error:  # например, целое длиннее 4300 цифр
            raise SerializationError(f"Некорректный JSON: {error}") from error
        except RecursionError:
            raise SerializationError(
                "Слишком глубокая вложенность в JSON"
            ) from None
        if expected is not None and not isinstance(result, expected):
            raise SerializationError(
                f"Ожидался объект {expected.__name__}, а в JSON — "
                f"{type(result).__name__}"
            )
        return result

    def save(self, obj: object, path: str | Path) -> None:
        """Записать объект в файл в кодировке UTF-8 с переводами строк LF.

        JSON строится до открытия файла, поэтому ошибка сериализации не
        портит уже существующий файл.

        :raises SerializationError: если объект нельзя записать в JSON.
        :raises OSError: если файл не удалось записать.
        """
        text = self.dumps(obj)
        Path(path).write_text(text + "\n", encoding="utf-8", newline="\n")

    def load(self, path: str | Path, expected: type | None = None) -> Any:
        """Прочитать объект из файла (UTF-8, в том числе с меткой BOM).

        :raises SerializationError: если содержимое не подходит.
        :raises OSError: если файл не удалось прочитать.
        """
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as error:
            raise SerializationError(
                "Файл не в кодировке UTF-8"
            ) from error
        return self.loads(text, expected)
