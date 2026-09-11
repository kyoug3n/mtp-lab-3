"""Тесты фигур (Средн. 4) и абстрактного класса Shape (Повыш. 9)."""
import inspect
import math
import random
import unittest

from shapelab.shapes import (
    Circle,
    Rectangle,
    Shape,
    Square,
    Triangle,
    format_number,
)


class AbstractShapeTests(unittest.TestCase):
    def test_shape_cannot_be_instantiated(self) -> None:
        with self.assertRaises(TypeError):
            Shape()  # type: ignore[abstract]

    def test_subclass_must_implement_every_abstract_method(self) -> None:
        class OnlyArea(Shape):
            NAME = "заготовка"
            SIZE_LABELS: dict[str, str] = {}

            def area(self) -> float:
                return 1.0

        with self.assertRaises(TypeError) as caught:
            OnlyArea()  # type: ignore[abstract]
        self.assertIn("perimeter", str(caught.exception))

    def test_complete_subclass_gets_common_behaviour(self) -> None:
        class UnitSquare(Shape):
            NAME = "единичный квадрат"
            SIZE_LABELS: dict[str, str] = {}

            def area(self) -> float:
                return 1.0

            def perimeter(self) -> float:
                return 4.0

        shape = UnitSquare()
        self.assertEqual(
            shape.describe(),
            "Единичный квадрат: площадь 1, периметр 4",
        )
        self.assertEqual(repr(shape), "UnitSquare()")

    def test_concrete_shapes_are_shapes(self) -> None:
        for shape in (Circle(1), Rectangle(1, 2), Square(3)):
            with self.subTest(shape=shape):
                self.assertIsInstance(shape, Shape)


class SubclassContractTests(unittest.TestCase):
    """Контракт SIZE_LABELS проверяется при объявлении класса фигуры."""

    def test_real_shapes_follow_the_contract(self) -> None:
        for cls in (Circle, Rectangle, Square, Triangle):
            with self.subTest(cls=cls):
                parameters = list(inspect.signature(cls).parameters)
                self.assertEqual(parameters, list(cls.SIZE_LABELS))

    def test_extra_constructor_parameter(self) -> None:
        # Без проверки цвет молча терялся бы при записи в JSON.
        with self.assertRaisesRegex(
            TypeError, r"^ColoredCircle: параметры конструктора "
                       r"\(radius, color\) не совпадают с SIZE_LABELS "
                       r"\(radius\)$"
        ):
            class ColoredCircle(Circle):
                def __init__(self, radius: float, color: str) -> None:
                    super().__init__(radius)
                    self.color = color

    def test_label_without_constructor_parameter(self) -> None:
        with self.assertRaisesRegex(TypeError, "не совпадают с SIZE_LABELS"):
            class LabelledSquare(Square):
                SIZE_LABELS = {"side": "сторона", "color": "цвет"}

    def test_positional_only_parameter(self) -> None:
        # from_dict передаёт размеры по именам: cls(**data).
        with self.assertRaisesRegex(TypeError, "не совпадают с SIZE_LABELS"):
            class PositionalCircle(Circle):
                def __init__(self, radius: float, /) -> None:
                    super().__init__(radius)

    def test_size_without_property(self) -> None:
        with self.assertRaisesRegex(TypeError, "для размера side нет"):
            class Plain(Shape):
                NAME = "фигура без свойства"
                SIZE_LABELS = {"side": "сторона"}

                def __init__(self, side: float) -> None:
                    self._side = side

                def area(self) -> float:
                    return 1.0

                def perimeter(self) -> float:
                    return 1.0

    def test_missing_class_attributes(self) -> None:
        with self.assertRaisesRegex(TypeError, "не задан атрибут класса NAME"):
            class Nameless(Shape):
                SIZE_LABELS: dict[str, str] = {}

                def area(self) -> float:
                    return 1.0

                def perimeter(self) -> float:
                    return 1.0

    def test_abstract_subclasses_are_not_checked(self) -> None:
        class StillAbstract(Shape):
            def extra(self, colour: str) -> str:
                return colour

        self.assertTrue(inspect.isabstract(StillAbstract))

    def test_correct_subclass_round_trips(self) -> None:
        class Coin(Circle):
            NAME = "монета"

        coin = Coin(1)
        self.assertEqual(Coin.from_dict(coin.to_dict()), coin)
        self.assertEqual(coin.describe()[:6], "Монета")


class MeasureTests(unittest.TestCase):
    def test_circle(self) -> None:
        circle = Circle(2)
        self.assertAlmostEqual(circle.area(), 4 * math.pi)
        self.assertAlmostEqual(circle.perimeter(), 4 * math.pi)

    def test_rectangle(self) -> None:
        rectangle = Rectangle(3, 4.5)
        self.assertEqual(rectangle.area(), 13.5)
        self.assertEqual(rectangle.perimeter(), 15.0)

    def test_square_matches_rectangle_with_equal_sides(self) -> None:
        rng = random.Random(4)
        for _ in range(1000):
            side = rng.uniform(1e-3, 1e3)
            square, rectangle = Square(side), Rectangle(side, side)
            self.assertEqual(square.area(), rectangle.area())
            self.assertEqual(square.perimeter(), rectangle.perimeter())

    def test_measures_are_floats_even_for_integer_sizes(self) -> None:
        for shape in (Circle(1), Rectangle(2, 3), Square(4)):
            with self.subTest(shape=shape):
                self.assertIsInstance(shape.area(), float)
                self.assertIsInstance(shape.perimeter(), float)

    def test_scaling_law(self) -> None:
        # При увеличении размеров в k раз площадь растёт в k², а периметр —
        # в k раз. Проверка одинакова для всех фигур благодаря полиморфизму.
        k = 3
        pairs = [
            (Circle(1.5), Circle(1.5 * k)),
            (Rectangle(2, 7), Rectangle(2 * k, 7 * k)),
            (Square(0.5), Square(0.5 * k)),
        ]
        for small, big in pairs:
            with self.subTest(shape=small):
                self.assertAlmostEqual(big.area(), small.area() * k * k)
                self.assertAlmostEqual(big.perimeter(), small.perimeter() * k)


class ValidationTests(unittest.TestCase):
    def test_rejects_non_positive_sizes(self) -> None:
        for make in (Circle, Square, lambda x: Rectangle(1, x)):
            for value in (0, -1, -0.5, 0.0):
                with self.subTest(make=make, value=value):
                    with self.assertRaises(ValueError):
                        make(value)

    def test_rejects_non_numbers_including_bool(self) -> None:
        for value in ("2", None, [2], True, False, 2j):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    Circle(value)  # type: ignore[arg-type]

    def test_rejects_infinity_nan_and_huge_integers(self) -> None:
        for value in (math.inf, -math.inf, math.nan, 10**400):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Square(value)

    def test_error_names_the_wrong_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "^Высота: .*получено -2$"):
            Rectangle(1, -2)
        with self.assertRaisesRegex(ValueError, "^Сторона: "):
            Square(0)

    def test_rejects_shapes_whose_measures_do_not_fit_float(self) -> None:
        with self.assertRaisesRegex(ValueError, "слишком велики"):
            Circle(1e200)
        with self.assertRaisesRegex(ValueError, "слишком малы"):
            Square(1e-200)
        # Сами размеры допустимы — это просто большой и маленький круги.
        self.assertTrue(math.isfinite(Circle(1e150).area()))
        self.assertGreater(Square(1e-150).area(), 0)


class EncapsulationTests(unittest.TestCase):
    def test_sizes_are_read_only(self) -> None:
        circle = Circle(2)
        with self.assertRaises(AttributeError):
            circle.radius = -5  # type: ignore[misc]
        self.assertEqual(circle.radius, 2)

    def test_sizes_keep_original_type(self) -> None:
        self.assertEqual(Rectangle(3, 4.5).sizes(),
                         {"width": 3, "height": 4.5})
        self.assertIsInstance(Square(2).side, int)


class ComparisonTests(unittest.TestCase):
    def test_equal_shapes(self) -> None:
        self.assertEqual(Circle(2), Circle(2))
        self.assertEqual(Circle(2), Circle(2.0))
        self.assertNotEqual(Circle(2), Circle(3))

    def test_square_is_not_equal_to_rectangle(self) -> None:
        # Геометрически это одна фигура, но классы разные.
        self.assertNotEqual(Square(2), Rectangle(2, 2))
        self.assertIsInstance(Square(2), Rectangle)

    def test_hash_allows_sets(self) -> None:
        shapes = {Circle(1), Circle(1.0), Square(1), Rectangle(1, 1)}
        self.assertEqual(len(shapes), 3)

    def test_not_equal_to_other_objects(self) -> None:
        self.assertNotEqual(Circle(1), 1)
        self.assertNotEqual(Circle(1), "Circle(radius=1)")


class OutputTests(unittest.TestCase):
    def test_describe(self) -> None:
        self.assertEqual(
            Square(0.1).describe(),
            "Квадрат (сторона = 0.1): площадь 0.01, периметр 0.4",
        )

    def test_repr(self) -> None:
        self.assertEqual(repr(Rectangle(3, 4.5)),
                         "Rectangle(width=3, height=4.5)")
        self.assertEqual(repr(Square(2)), "Square(side=2)")

    def test_repr_recreates_equal_shape(self) -> None:
        for shape in (Circle(0.1), Rectangle(1e-3, 7), Square(10**20)):
            with self.subTest(shape=shape):
                self.assertEqual(eval(repr(shape)), shape)

    def test_format_number(self) -> None:
        self.assertEqual(format_number(10**20), str(10**20))
        self.assertEqual(format_number(1234567.0), "1.23457e+06")
        self.assertEqual(format_number(1234567.0, 12), "1234567")


if __name__ == "__main__":
    unittest.main()
