"""Средн. 10: чертёж — набор фигур, который обходится классом-итератором.

Протокол итерации в Python состоит из двух методов: ``__iter__`` выдаёт
итератор, а ``__next__`` итератора возвращает очередной элемент или бросает
``StopIteration``, когда элементы кончились. На этом протоколе работают
``for``, ``list()``, ``sum()``, ``in`` и распаковка.

Здесь роли разделены между двумя классами. :class:`Drawing` — итерируемый
объект: его ``__iter__`` каждый раз создаёт новый :class:`DrawingIterator`,
поэтому чертёж можно обходить сколько угодно раз, в том числе двумя
вложенными циклами. Сам итератор одноразовый: он помнит, до какой фигуры
дошёл, и после конца всегда бросает ``StopIteration``.
"""
import math
from collections.abc import Iterable
from typing import Any

from shapelab.serializer import Serializable
from shapelab.shapes import Shape


class Drawing(Serializable):
    """Чертёж: фигуры в порядке добавления.

    >>> from shapelab.shapes import Circle, Square
    >>> drawing = Drawing([Circle(1), Square(2)])
    >>> for shape in drawing:
    ...     print(shape.describe())
    Круг (радиус = 1): площадь 3.14159, периметр 6.28319
    Квадрат (сторона = 2): площадь 4, периметр 8
    >>> iterator = iter(drawing)
    >>> next(iterator), next(iterator)
    (Circle(radius=1), Square(side=2))
    >>> next(iterator)
    Traceback (most recent call last):
    ...
    StopIteration
    """

    def __init__(self, shapes: Iterable[Shape] = ()) -> None:
        self._shapes: list[Shape] = []
        # Номер изменения: итератор сверяет его, чтобы заметить, что чертёж
        # изменили во время обхода.
        self._version = 0
        for shape in shapes:
            self.add(shape)

    def add(self, shape: Shape) -> None:
        """Добавить фигуру в конец чертежа.

        :raises TypeError: если ``shape`` не фигура.
        """
        if not isinstance(shape, Shape):
            raise TypeError(
                f"На чертеже могут быть только фигуры, получено {shape!r}"
            )
        self._shapes.append(shape)
        self._version += 1

    def total_area(self) -> float:
        """Суммарная площадь фигур (``inf``, если сумма больше 1e308).

        Сумма считается :func:`math.fsum` — без накопления ошибок
        округления, от порядка фигур результат не зависит.
        """
        try:
            return math.fsum(shape.area() for shape in self)
        except OverflowError:
            return math.inf

    def to_dict(self) -> dict[str, Any]:
        """Поля для JSON: список фигур (их запишет сериализатор)."""
        return {"shapes": list(self)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Drawing":
        """Создать чертёж из списка уже восстановленных фигур.

        :raises TypeError: если ``shapes`` не список или в нём не фигуры.
        """
        cls.check_fields(data, ["shapes"])
        shapes = data["shapes"]
        if not isinstance(shapes, list):
            raise TypeError("поле «shapes» должно быть списком фигур")
        return cls(shapes)

    def __iter__(self) -> "DrawingIterator":
        return DrawingIterator(self)

    def __len__(self) -> int:
        return len(self._shapes)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Drawing):
            return NotImplemented
        return self._shapes == other._shapes

    def __repr__(self) -> str:
        return f"Drawing({self._shapes!r})"


class DrawingIterator:
    """Итератор по фигурам чертежа.

    Итератор читает защищённые атрибуты чертежа: оба класса — части одной
    структуры данных и описаны в одном модуле.
    """

    def __init__(self, drawing: Drawing) -> None:
        self._drawing = drawing
        self._version = drawing._version
        self._index = 0
        self._finished = False

    def __iter__(self) -> "DrawingIterator":
        """Итератор тоже итерируем: возвращает сам себя."""
        return self

    def __next__(self) -> Shape:
        """Следующая фигура.

        :raises StopIteration: если фигуры кончились — и при всех следующих
            вызовах, даже если на чертёж потом добавили фигуры.
        :raises RuntimeError: если чертёж изменился во время обхода — как у
            словаря, иначе добавленные фигуры попадали бы в обход
            непредсказуемо.
        """
        if self._finished:
            raise StopIteration
        if self._drawing._version != self._version:
            raise RuntimeError("Чертёж изменился во время обхода")
        shapes = self._drawing._shapes
        if self._index >= len(shapes):
            self._finished = True
            raise StopIteration
        shape = shapes[self._index]
        self._index += 1
        return shape
