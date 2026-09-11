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

    def _shape_at(self, index: int) -> Shape | None:
        """Фигура номер ``index`` или ``None``, если фигур меньше.

        Внутренний интерфейс для :class:`DrawingIterator`: итератор не
        знает, как чертёж хранит фигуры.
        """
        if index < len(self._shapes):
            return self._shapes[index]
        return None

    def _current_version(self) -> int:
        """Номер последнего изменения — для :class:`DrawingIterator`."""
        return self._version

    def __len__(self) -> int:
        return len(self._shapes)

    def __eq__(self, other: object) -> bool:
        """Чертежи равны, если равны их фигуры по порядку.

        Фигуры другого чертежа берутся его же итератором, а не из его
        защищённого списка.
        """
        if not isinstance(other, Drawing):
            return NotImplemented
        return list(self) == list(other)

    def __repr__(self) -> str:
        return f"Drawing({self._shapes!r})"


class DrawingIterator:
    """Итератор по фигурам чертежа.

    С чертежом итератор общается только через два внутренних метода —
    ``_shape_at`` и ``_current_version``, — а не через его атрибуты.
    """

    def __init__(self, drawing: Drawing) -> None:
        self._drawing = drawing
        self._version = drawing._current_version()
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
        if self._drawing._current_version() != self._version:
            raise RuntimeError("Чертёж изменился во время обхода")
        shape = self._drawing._shape_at(self._index)
        if shape is None:
            self._finished = True
            raise StopIteration
        self._index += 1
        return shape
