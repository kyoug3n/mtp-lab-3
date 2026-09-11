"""Тесты чертежа и класса-итератора (Средн. 10)."""
import math
import unittest

from shapelab.drawing import Drawing, DrawingIterator
from shapelab.shapes import Circle, Rectangle, Square, Triangle

SHAPES = [Circle(1), Rectangle(2, 3), Square(4), Triangle(3, 4, 5)]


class IterationProtocolTests(unittest.TestCase):
    def test_iter_returns_our_iterator_class(self) -> None:
        iterator = iter(Drawing(SHAPES))
        self.assertIsInstance(iterator, DrawingIterator)
        self.assertIs(iter(iterator), iterator)

    def test_manual_next_until_stop_iteration(self) -> None:
        iterator = iter(Drawing(SHAPES[:2]))
        self.assertEqual(next(iterator), Circle(1))
        self.assertEqual(next(iterator), Rectangle(2, 3))
        with self.assertRaises(StopIteration):
            next(iterator)

    def test_for_loop_keeps_order(self) -> None:
        visited = []
        for shape in Drawing(SHAPES):
            visited.append(shape)
        self.assertEqual(visited, SHAPES)

    def test_empty_drawing(self) -> None:
        self.assertEqual(list(Drawing()), [])
        self.assertEqual(len(Drawing()), 0)

    def test_builtins_work_through_the_protocol(self) -> None:
        drawing = Drawing(SHAPES)
        self.assertIn(Square(4), drawing)
        self.assertNotIn(Square(5), drawing)
        largest = max(drawing, key=lambda shape: shape.area())
        self.assertEqual(largest, Square(4))
        first, *_, last = drawing
        self.assertEqual((first, last), (Circle(1), Triangle(3, 4, 5)))


class ReuseTests(unittest.TestCase):
    def test_drawing_can_be_traversed_many_times(self) -> None:
        drawing = Drawing(SHAPES)
        self.assertEqual(list(drawing), list(drawing))

    def test_iterator_is_single_use(self) -> None:
        iterator = iter(Drawing(SHAPES))
        self.assertEqual(list(iterator), SHAPES)
        self.assertEqual(list(iterator), [])

    def test_nested_loops_use_independent_iterators(self) -> None:
        drawing = Drawing(SHAPES)
        pairs = [(a, b) for a in drawing for b in drawing]
        self.assertEqual(len(pairs), len(SHAPES) ** 2)

    def test_exhausted_iterator_stays_exhausted(self) -> None:
        drawing = Drawing([Circle(1)])
        iterator = iter(drawing)
        self.assertEqual(list(iterator), [Circle(1)])
        drawing.add(Square(1))
        for _ in range(3):
            with self.assertRaises(StopIteration):
                next(iterator)


class ModificationTests(unittest.TestCase):
    def test_adding_during_iteration_is_an_error(self) -> None:
        drawing = Drawing(SHAPES)
        with self.assertRaisesRegex(RuntimeError, "изменился во время"):
            for shape in drawing:
                drawing.add(shape)

    def test_new_iterator_sees_added_shapes(self) -> None:
        drawing = Drawing([Circle(1)])
        drawing.add(Square(2))
        self.assertEqual(list(drawing), [Circle(1), Square(2)])

    def test_rejects_non_shapes(self) -> None:
        for bad in (Circle, 5, None, "круг", Drawing()):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    Drawing().add(bad)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            Drawing([Circle(1), 2])  # type: ignore[list-item]


class TotalAreaTests(unittest.TestCase):
    def test_sum_of_areas(self) -> None:
        drawing = Drawing(SHAPES)
        expected = math.pi + 6 + 16 + 6
        self.assertAlmostEqual(drawing.total_area(), expected)
        self.assertEqual(Drawing().total_area(), 0.0)

    def test_sum_is_exactly_rounded(self) -> None:
        # Сложение по одному 1e16 + 1 + 1 + … теряет единицы: у чисел
        # около 1e16 соседние float отличаются на 2. fsum — не теряет.
        drawing = Drawing([Rectangle(1e8, 1e8)] + [Square(1)] * 10)
        naive = 0.0
        for shape in drawing:
            naive += shape.area()
        self.assertEqual(naive, 1e16)
        self.assertEqual(drawing.total_area(), 1e16 + 10)

    def test_overflowing_sum_is_infinity(self) -> None:
        drawing = Drawing([Square(1e154)] * 2)
        self.assertEqual(drawing.total_area(), math.inf)


class ComparisonTests(unittest.TestCase):
    def test_equality_and_repr(self) -> None:
        self.assertEqual(Drawing([Circle(1)]), Drawing([Circle(1.0)]))
        self.assertNotEqual(Drawing([Circle(1)]), Drawing([Circle(2)]))
        self.assertEqual(repr(Drawing([Square(2)])),
                         "Drawing([Square(side=2)])")


if __name__ == "__main__":
    unittest.main()
