"""Тесты треугольника и статического метода is_valid (Средн. 6)."""
import itertools
import math
import random
import unittest
from decimal import Decimal, localcontext
from fractions import Fraction

from shapelab.shapes import Shape, Triangle


def exact_area(a: float, b: float, c: float) -> float:
    """Площадь по формуле Герона, вычисленная точно и округлённая в конце.

    16·S² = (a + b + c)(−a + b + c)(a − b + c)(a + b − c) считается в
    рациональных числах без округлений, корень — в Decimal с 50 цифрами.
    """
    a_, b_, c_ = (Fraction(side) for side in (a, b, c))
    square = (a_ + b_ + c_) * (-a_ + b_ + c_) * (a_ - b_ + c_) * (
        a_ + b_ - c_) / 16
    with localcontext() as context:
        context.prec = 50
        return float(
            (Decimal(square.numerator) / Decimal(square.denominator)).sqrt()
        )


def naive_heron(a: float, b: float, c: float) -> float:
    """Формула Герона в обычной записи — для сравнения."""
    p = (a + b + c) / 2
    return math.sqrt(p * (p - a) * (p - b) * (p - c))


class IsValidTests(unittest.TestCase):
    def test_is_a_static_method(self) -> None:
        self.assertIsInstance(Triangle.__dict__["is_valid"], staticmethod)
        # Вызывается без объекта и через объект одинаково.
        self.assertTrue(Triangle.is_valid(3, 4, 5))
        self.assertFalse(Triangle(3, 4, 5).is_valid(1, 2, 10))

    def test_known_cases_in_any_order(self) -> None:
        cases = [
            ((3, 4, 5), True),
            ((2, 2, 2), True),
            ((2, 2, 3.999), True),
            ((1, 2, 3), False),     # вырожденный: отрезок
            ((1, 2, 10), False),
            ((0, 1, 1), False),
            ((-3, 4, 5), False),
        ]
        for sides, expected in cases:
            for order in itertools.permutations(sides):
                with self.subTest(sides=order):
                    self.assertIs(Triangle.is_valid(*order), expected)

    def test_non_lengths_give_false_instead_of_errors(self) -> None:
        for bad in ("3", None, True, math.nan, math.inf, 10**400, 3j):
            with self.subTest(bad=bad):
                self.assertIs(Triangle.is_valid(bad, 4, 5), False)

    def test_comparison_is_exact(self) -> None:
        big = 2**53
        # float(big + 1) == big, поэтому сравнение во float сочло бы
        # 2**53 + 1, 2**53, 1 невырожденным треугольником.
        self.assertTrue(float(big + 1) - big < 1)
        self.assertFalse(Triangle.is_valid(big + 1, big, 1))
        self.assertTrue(Triangle.is_valid(big + 1, big, 1.5))
        # Во float 0.1 + 0.2 > 0.3, а 0.1 + 0.7 < 0.8.
        self.assertTrue(Triangle.is_valid(0.1, 0.2, 0.3))
        self.assertFalse(Triangle.is_valid(0.1, 0.7, 0.8))

    def test_agrees_with_constructor(self) -> None:
        for sides in itertools.product(range(-1, 8), repeat=3):
            with self.subTest(sides=sides):
                if Triangle.is_valid(*sides):
                    Triangle(*sides)
                else:
                    with self.assertRaises(ValueError):
                        Triangle(*sides)


class TriangleTests(unittest.TestCase):
    def test_right_triangle(self) -> None:
        triangle = Triangle(3, 4, 5)
        self.assertEqual(triangle.area(), 6.0)
        self.assertEqual(triangle.perimeter(), 12.0)
        self.assertIsInstance(triangle, Shape)

    def test_equilateral(self) -> None:
        self.assertAlmostEqual(Triangle(2, 2, 2).area(), math.sqrt(3))

    def test_error_messages(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "^Из сторон 3, 1, 2 треугольник не построить: "
                        "3 ≥ 1 \\+ 2$"
        ):
            Triangle(3, 1, 2)
        with self.assertRaisesRegex(ValueError, "^Сторона b: "):
            Triangle(3, -4, 5)
        with self.assertRaises(TypeError):
            Triangle(3, 4, "5")  # type: ignore[arg-type]

    def test_describe_and_repr(self) -> None:
        triangle = Triangle(3, 4, 5)
        self.assertEqual(
            triangle.describe(),
            "Треугольник (сторона a = 3, сторона b = 4, сторона c = 5): "
            "площадь 6, периметр 12",
        )
        self.assertEqual(repr(triangle), "Triangle(a=3, b=4, c=5)")
        self.assertEqual(eval(repr(triangle)), triangle)

    def test_sides_are_read_only(self) -> None:
        triangle = Triangle(3, 4, 5)
        with self.assertRaises(AttributeError):
            triangle.c = 100  # type: ignore[misc]


class AreaAccuracyTests(unittest.TestCase):
    def test_matches_shoelace_formula_on_random_triangles(self) -> None:
        # Площадь по координатам вершин (формула шнурования) считается
        # точно в целых числах; стороны — расстояния между вершинами.
        rng = random.Random(4)
        checked = 0
        for _ in range(3000):
            points = [(rng.randint(-1000, 1000), rng.randint(-1000, 1000))
                      for _ in range(3)]
            (x1, y1), (x2, y2), (x3, y3) = points
            doubled = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            sides = [math.dist(p, q)
                     for p, q in itertools.combinations(points, 2)]
            if doubled == 0 or not Triangle.is_valid(*sides):
                continue
            checked += 1
            self.assertAlmostEqual(
                Triangle(*sides).area() / (doubled / 2), 1, delta=1e-7,
                msg=str(points),
            )
        self.assertGreater(checked, 2900)

    def test_needle_triangles_are_accurate(self) -> None:
        # Две почти равные длинные стороны и одна короткая.
        rng = random.Random(4)
        for _ in range(1000):
            a = rng.uniform(1, 1000)
            b = a * (1 + rng.uniform(-1e-6, 1e-6))
            c = a * rng.uniform(1e-9, 1e-3)
            expected = exact_area(a, b, c)
            relative_error = abs(Triangle(a, b, c).area() - expected) / (
                expected)
            self.assertLess(relative_error, 1e-14, msg=f"{a}, {b}, {c}")

    def test_naive_formula_fails_where_ours_does_not(self) -> None:
        cases = [(0.1, 0.2, 0.3), (1e8, 1e8, 1e-3),
                 (100000, 99999.99979, 0.00029)]
        for sides in cases:
            with self.subTest(sides=sides):
                expected = exact_area(*sides)
                self.assertAlmostEqual(Triangle(*sides).area() / expected, 1,
                                       delta=1e-15)
                self.assertGreater(
                    abs(naive_heron(*sides) / expected - 1), 1e-8
                )

    def test_huge_triangle_does_not_overflow_early(self) -> None:
        # Произведение четырёх множителей ~1e600 не помещается во float,
        # а сама площадь ~4.3e299 помещается.
        side = 1e150
        self.assertAlmostEqual(
            Triangle(side, side, side).area() / (math.sqrt(3) / 4 * side**2),
            1, delta=1e-15,
        )


if __name__ == "__main__":
    unittest.main()
