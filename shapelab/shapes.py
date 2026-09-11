"""Средн. 4 и Повыш. 9: геометрические фигуры с общим абстрактным классом.

:class:`Shape` задаёт интерфейс любой фигуры — площадь и периметр — и
объявляет эти методы абстрактными (модуль ``abc``). Создать «просто фигуру»
или наследника, забывшего реализовать один из них, нельзя: Python откажет
ещё при создании объекта, а не при первом вызове метода.

Размеры хранятся в защищённых атрибутах и доступны только через свойства
без записи, поэтому фигура после создания не меняется: проверки
конструктора нельзя обойти, а фигуры можно сравнивать и класть в множества.
"""
import math
from abc import ABC, abstractmethod
from typing import ClassVar

Number = int | float


def format_number(value: Number, significant: int = 6) -> str:
    """Записать число коротко: целые — как есть, дробные — ``significant``
    значащими цифрами без лишних нулей.

    >>> format_number(12.566370614359172)
    '12.5664'
    >>> format_number(2), format_number(2.0), format_number(0.1 + 0.2)
    ('2', '2', '0.3')
    """
    if isinstance(value, int):
        return str(value)
    return f"{value:.{significant}g}"


class Shape(ABC):
    """Абстрактная фигура: у всякой фигуры есть площадь и периметр.

    Наследник обязан реализовать :meth:`area` и :meth:`perimeter` и задать
    атрибуты класса ``NAME`` (название для вывода) и ``SIZE_LABELS``
    (имена параметров конструктора → подписи). Для каждого имени из
    ``SIZE_LABELS`` у фигуры должно быть одноимённое свойство. Остальное —
    описание, сравнение, ``repr`` — базовый класс делает сам.

    >>> Shape()  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    TypeError: Can't instantiate abstract class Shape ...
    """

    NAME: ClassVar[str]
    SIZE_LABELS: ClassVar[dict[str, str]]

    @abstractmethod
    def area(self) -> float:
        """Площадь фигуры."""

    @abstractmethod
    def perimeter(self) -> float:
        """Периметр фигуры."""

    @staticmethod
    def check_length(value: object, label: str) -> None:
        """Проверить, что ``value`` годится как длина: число больше нуля.

        Метод статический — ему не нужны ни объект, ни класс, только само
        значение. ``bool`` отклоняется, хотя в Python это подкласс ``int``.

        :raises TypeError: если ``value`` не число.
        :raises ValueError: если число не больше нуля или бесконечно.
        """
        label = label.capitalize()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{label}: нужно число, получено {value!r}")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            raise ValueError(f"{label}: число больше 1e308 не помещается "
                             "во float") from None
        if not finite:
            raise ValueError(f"{label}: нужно конечное число, получено "
                             f"{value}")
        if value <= 0:
            raise ValueError(f"{label}: нужно число больше нуля, получено "
                             f"{format_number(value, 12)}")

    def sizes(self) -> dict[str, Number]:
        """Размеры фигуры по именам параметров конструктора.

        >>> Rectangle(3, 4).sizes()
        {'width': 3, 'height': 4}
        """
        return {name: getattr(self, name) for name in self.SIZE_LABELS}

    def describe(self) -> str:
        """Описание для вывода: название, размеры, площадь и периметр.

        Метод один на все фигуры, но площадь и периметр для каждой считает
        её собственный класс — это полиморфизм.

        >>> print(Circle(2).describe())
        Круг (радиус = 2): площадь 12.5664, периметр 12.5664
        """
        sizes = ", ".join(
            f"{self.SIZE_LABELS[name]} = {format_number(value, 12)}"
            for name, value in self.sizes().items()
        )
        title = self.NAME.capitalize()
        if sizes:
            title += f" ({sizes})"
        return (f"{title}: "
                f"площадь {format_number(self.area())}, "
                f"периметр {format_number(self.perimeter())}")

    def _check_measures(self) -> None:
        """Убедиться, что площадь и периметр представимы числом ``float``.

        Вызывается в конце конструктора: например, у круга радиуса 1e200
        площадь переполняет ``float``, а у квадрата со стороной 1e-200
        округляется до нуля — такие фигуры не создаются.
        """
        name = self.NAME.capitalize()
        for label, value in (("площадь", self.area()),
                             ("периметр", self.perimeter())):
            if value == math.inf:
                raise ValueError(f"{name}: {label} больше 1e308, "
                                 "размеры слишком велики")
            if value == 0:
                raise ValueError(f"{name}: {label} округляется до "
                                 "нуля, размеры слишком малы")

    def __eq__(self, other: object) -> bool:
        """Фигуры равны, если у них один класс и одинаковые размеры."""
        if not isinstance(other, Shape):
            return NotImplemented
        return type(self) is type(other) and self.sizes() == other.sizes()

    def __hash__(self) -> int:
        return hash((type(self).__name__, tuple(self.sizes().items())))

    def __repr__(self) -> str:
        arguments = ", ".join(
            f"{name}={value!r}" for name, value in self.sizes().items()
        )
        return f"{type(self).__name__}({arguments})"


class Circle(Shape):
    """Круг с заданным радиусом.

    >>> Circle(1).area() == math.pi
    True
    """

    NAME = "круг"
    SIZE_LABELS = {"radius": "радиус"}

    def __init__(self, radius: Number) -> None:
        self.check_length(radius, "радиус")
        self._radius = radius
        self._check_measures()

    @property
    def radius(self) -> Number:
        """Радиус круга."""
        return self._radius

    def area(self) -> float:
        # r * r, а не r ** 2: при переполнении умножение даёт inf,
        # а возведение float в степень бросает OverflowError.
        radius = float(self._radius)
        return math.pi * radius * radius

    def perimeter(self) -> float:
        return 2 * math.pi * float(self._radius)


class Rectangle(Shape):
    """Прямоугольник с заданными шириной и высотой.

    >>> print(Rectangle(3, 4).describe())
    Прямоугольник (ширина = 3, высота = 4): площадь 12, периметр 14
    """

    NAME = "прямоугольник"
    SIZE_LABELS = {"width": "ширина", "height": "высота"}

    def __init__(self, width: Number, height: Number) -> None:
        self.check_length(width, "ширина")
        self.check_length(height, "высота")
        self._width = width
        self._height = height
        self._check_measures()

    @property
    def width(self) -> Number:
        """Ширина прямоугольника."""
        return self._width

    @property
    def height(self) -> Number:
        """Высота прямоугольника."""
        return self._height

    def area(self) -> float:
        return float(self._width) * float(self._height)

    def perimeter(self) -> float:
        return 2 * (float(self._width) + float(self._height))


class Square(Rectangle):
    """Квадрат — прямоугольник с равными сторонами.

    Площадь и периметр наследуются от :class:`Rectangle` без изменений.
    Наследование здесь безопасно, потому что фигуры неизменяемы: у квадрата
    нельзя поменять одну ширину и получить «квадрат» 2 × 3.

    >>> square = Square(5)
    >>> isinstance(square, Rectangle), square.area(), square.perimeter()
    (True, 25.0, 20.0)
    """

    NAME = "квадрат"
    SIZE_LABELS = {"side": "сторона"}

    def __init__(self, side: Number) -> None:
        # Проверка до вызова родителя — чтобы ошибка называла сторону,
        # а не ширину.
        self.check_length(side, "сторона")
        super().__init__(side, side)

    @property
    def side(self) -> Number:
        """Сторона квадрата."""
        return self.width
