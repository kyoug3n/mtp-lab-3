"""Тесты интерактивного меню."""
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from shapelab import menu
from shapelab.console import ScriptedConsole
from shapelab.drawing import Drawing
from shapelab.menu import SERIALIZER, ShapeMenu
from shapelab.shapes import Circle, Rectangle, Shape, Square, Triangle

ADD, SHOW, SAVE, LOAD, EXIT = "1", "2", "3", "4", "0"


class MenuTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def run_menu(
        self, lines: list[str], drawing: Drawing | None = None
    ) -> tuple[ShapeMenu, ScriptedConsole]:
        console = ScriptedConsole(lines)
        shape_menu = ShapeMenu(console.input, console.print, self.directory)
        if drawing is not None:
            shape_menu.drawing = drawing
        shape_menu.run()
        return shape_menu, console


class MainLoopTests(MenuTestCase):
    def test_exit_by_zero_word_or_end_of_input(self) -> None:
        for lines in ([EXIT], ["выход"], []):
            with self.subTest(lines=lines):
                _, console = self.run_menu(lines)
                self.assertEqual(console.transcript[-1], "До свидания!")

    def test_unknown_items(self) -> None:
        for choice in ("9", "", "01", "один", "9" * 5000):
            with self.subTest(choice=choice[:10]):
                _, console = self.run_menu([choice])
                self.assertIn(f"Нет такого пункта: {choice!r}.",
                              console.transcript)


class AddShapeTests(MenuTestCase):
    def test_every_kind_of_shape(self) -> None:
        cases = [
            (Circle, ["1", "2"], Circle(2)),
            (Rectangle, ["2", "3", "4,5"], Rectangle(3, 4.5)),
            (Square, ["3", "0.1"], Square(0.1)),
            (Triangle, ["4", "3", "4", "5"], Triangle(3, 4, 5)),
        ]
        for cls, answers, expected in cases:
            with self.subTest(cls=cls):
                shape_menu, console = self.run_menu([ADD, *answers])
                self.assertEqual(list(shape_menu.drawing), [expected])
                self.assertIn(f"Добавлено: {expected.describe()}",
                              console.transcript)

    def test_questions_come_from_size_labels(self) -> None:
        _, console = self.run_menu([ADD, "4", "3", "4", "5"])
        prompts = [line.split(":")[0] for line in console.transcript
                   if line.startswith("Сторона ")]
        self.assertEqual(prompts, ["Сторона a", "Сторона b", "Сторона c"])

    def test_wrong_kind_is_asked_again(self) -> None:
        shape_menu, console = self.run_menu([ADD, "5", "круг", "3", "7"])
        self.assertIn("Нет такого вида: '5'.", console.transcript)
        self.assertIn("Нет такого вида: 'круг'.", console.transcript)
        self.assertEqual(list(shape_menu.drawing), [Square(7)])

    def test_wrong_sizes_are_asked_again(self) -> None:
        shape_menu, console = self.run_menu([ADD, "1", "-2", "abc", "2"])
        self.assertIn("Нужно число больше нуля.", console.transcript)
        self.assertIn("Нужно число, например 2 или 1,5.", console.transcript)
        self.assertEqual(list(shape_menu.drawing), [Circle(2)])

    def test_impossible_triangle_is_not_added(self) -> None:
        shape_menu, console = self.run_menu([ADD, "4", "1", "2", "10"])
        self.assertIn(
            "Фигура не добавлена. Из сторон 1, 2, 10 треугольник не "
            "построить: 10 ≥ 1 + 2.",
            console.transcript,
        )
        self.assertEqual(len(shape_menu.drawing), 0)

    def test_too_big_shape_is_not_added(self) -> None:
        shape_menu, console = self.run_menu([ADD, "1", "1e200"])
        self.assertIn("Фигура не добавлена. Круг: площадь больше 1e308, "
                      "размеры слишком велики.", console.transcript)
        self.assertEqual(len(shape_menu.drawing), 0)

    def test_exit_word_cancels_adding(self) -> None:
        shape_menu, console = self.run_menu([ADD, "2", "3", "выход", SHOW])
        self.assertEqual(len(shape_menu.drawing), 0)
        self.assertIn("На чертеже нет фигур.", console.transcript)

    def test_new_shape_class_appears_without_changing_menu(self) -> None:
        class Hexagon(Shape):
            NAME = "правильный шестиугольник"
            SIZE_LABELS = {"side": "сторона"}

            def __init__(self, side: float) -> None:
                self.check_length(side, "сторона")
                self._side = side

            @property
            def side(self) -> float:
                return self._side

            def area(self) -> float:
                return 3 * math.sqrt(3) / 2 * self._side ** 2

            def perimeter(self) -> float:
                return 6.0 * self._side

        classes = [*menu.SHAPE_CLASSES, Hexagon]
        with mock.patch.object(menu, "SHAPE_CLASSES", classes):
            shape_menu, console = self.run_menu([ADD, "5", "2"])
        self.assertIn("  5. Правильный шестиугольник", console.transcript)
        self.assertEqual(list(shape_menu.drawing), [Hexagon(2)])


class ShowDrawingTests(MenuTestCase):
    def test_empty(self) -> None:
        _, console = self.run_menu([SHOW])
        self.assertIn("На чертеже нет фигур.", console.transcript)

    def test_list_with_total_area(self) -> None:
        drawing = Drawing([Square(2), Triangle(3, 4, 5)])
        _, console = self.run_menu([SHOW], drawing)
        start = console.transcript.index("--- Показать чертёж ---")
        self.assertEqual(console.transcript[start + 1:start + 5], [
            "Фигур на чертеже: 2",
            "  1. Квадрат (сторона = 2): площадь 4, периметр 8",
            "  2. Треугольник (сторона a = 3, сторона b = 4, сторона c = 5):"
            " площадь 6, периметр 12",
            "Общая площадь: 10",
        ])

    def test_overflowing_total_area(self) -> None:
        # Каждый квадрат допустим, а их общая площадь больше 1e308.
        drawing = Drawing([Square(1e154), Square(1e154)])
        _, console = self.run_menu([SHOW], drawing)
        self.assertIn("  1. Квадрат (сторона = 1e+154): площадь 1e+308, "
                      "периметр 4e+154", console.transcript)
        self.assertIn("Общая площадь: больше 1e308", console.transcript)


class FileTests(MenuTestCase):
    def test_save_then_load_in_new_session(self) -> None:
        drawing = Drawing([Circle(2), Rectangle(3, 4.5)])
        _, console = self.run_menu([SAVE, "мой.json"], drawing)
        self.assertIn("Чертёж сохранён в мой.json (фигур: 2).",
                      console.transcript)
        shape_menu, console = self.run_menu([LOAD, "мой.json"])
        self.assertIn("Чертёж загружен из мой.json (фигур: 2).",
                      console.transcript)
        self.assertEqual(shape_menu.drawing, drawing)

    def test_enter_means_default_file(self) -> None:
        self.run_menu([SAVE, ""], Drawing([Square(1)]))
        path = self.directory / menu.DEFAULT_FILE
        self.assertEqual(SERIALIZER.load(path), Drawing([Square(1)]))

    def test_missing_file(self) -> None:
        _, console = self.run_menu([LOAD, "нет.json"])
        self.assertIn("Файл не найден: нет.json.", console.transcript)

    def test_bad_file_keeps_current_drawing(self) -> None:
        (self.directory / "bad.json").write_text("{", encoding="utf-8")
        (self.directory / "circle.json").write_text(
            SERIALIZER.dumps(Circle(1)), encoding="utf-8"
        )
        drawing = Drawing([Square(3)])
        shape_menu, console = self.run_menu(
            [LOAD, "bad.json", LOAD, "circle.json"], drawing
        )
        self.assertIn("Не удалось загрузить bad.json: Некорректный JSON: "
                      "Expecting property name enclosed in double quotes "
                      "(строка 1, столбец 2).", console.transcript)
        self.assertIn("Не удалось загрузить circle.json: Ожидался объект "
                      "Drawing, а в JSON — Circle.", console.transcript)
        self.assertEqual(shape_menu.drawing, Drawing([Square(3)]))

    def test_save_error(self) -> None:
        _, console = self.run_menu([SAVE, "нет/такой/папки.json"])
        self.assertTrue(any(
            line.startswith("Не удалось сохранить нет/такой/папки.json: ")
            for line in console.transcript
        ))


if __name__ == "__main__":
    unittest.main()
