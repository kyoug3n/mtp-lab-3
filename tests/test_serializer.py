"""Тесты JSON-сериализатора (Повыш. 5) и контракта Serializable (Повыш. 9)."""
import json
import random
import tempfile
import unittest
from pathlib import Path
from typing import Any

from shapelab.drawing import Drawing
from shapelab.serializer import (
    JsonSerializer,
    Serializable,
    SerializationError,
)
from shapelab.shapes import Circle, Rectangle, Shape, Square, Triangle

SHAPE_CLASSES = [Circle, Rectangle, Square, Triangle]


def make_serializer() -> JsonSerializer:
    return JsonSerializer([*SHAPE_CLASSES, Drawing])


class Point(Serializable):
    """Класс, не связанный с фигурами: сериализатор работает и с ним."""

    def __init__(self, x: int, y: int, label: str | None = None) -> None:
        self.x, self.y, self.label = x, y, label

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y, "label": self.label}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Point":
        cls.check_fields(data, ["x", "y", "label"])
        return cls(data["x"], data["y"], data["label"])

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Point) and vars(self) == vars(other)


class Holder(Serializable):
    """Хранит произвольное значение — для проверки ошибок записи."""

    def __init__(self, value: Any) -> None:
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Holder":
        return cls(data["value"])


def random_shape(rng: random.Random) -> Shape:
    def size() -> int | float:
        if rng.random() < 0.5:
            return rng.randint(1, 10**6)
        return rng.uniform(1e-3, 1e3)

    kind = rng.choice(SHAPE_CLASSES)
    if kind is Triangle:
        while True:
            sides = size(), size(), size()
            if Triangle.is_valid(*sides):
                return Triangle(*sides)
    if kind is Rectangle:
        return Rectangle(size(), size())
    return kind(size())


class SerializableContractTests(unittest.TestCase):
    def test_serializable_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            Serializable()  # type: ignore[abstract]

    def test_subclass_without_from_dict_is_abstract(self) -> None:
        class OnlyToDict(Serializable):
            def to_dict(self) -> dict[str, Any]:
                return {}

        with self.assertRaises(TypeError):
            OnlyToDict()  # type: ignore[abstract]

    def test_shapes_and_drawing_are_serializable(self) -> None:
        for cls in [*SHAPE_CLASSES, Drawing]:
            with self.subTest(cls=cls):
                self.assertTrue(issubclass(cls, Serializable))

    def test_check_fields(self) -> None:
        Serializable.check_fields({"a": 1, "b": 2}, ["a", "b"])
        cases = [
            ({"a": 1}, "нет поля «b»"),
            ({}, "нет полей «a», «b»"),
            ({"a": 1, "b": 2, "c": 3}, "лишнее поле «c»"),
            ({"a": 1, "b": 2, "c": 3, "d": 4}, "лишние поля «c», «d»"),
        ]
        for data, message in cases:
            with self.subTest(data=data):
                with self.assertRaisesRegex(ValueError, f"^{message}$"):
                    Serializable.check_fields(data, ["a", "b"])


class RegisterTests(unittest.TestCase):
    def test_rejects_non_serializable_and_abstract_classes(self) -> None:
        serializer = JsonSerializer()
        for bad in (int, object, Circle(1), "Circle", Shape, Serializable):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    serializer.register(bad)  # type: ignore[arg-type]

    def test_name_conflict(self) -> None:
        serializer = JsonSerializer([Point])
        serializer.register(Point)  # тот же класс повторно — можно

        class Point2(Point):
            pass

        Point2.__name__ = "Point"
        with self.assertRaises(ValueError):
            serializer.register(Point2)

    def test_register_works_as_decorator(self) -> None:
        serializer = JsonSerializer()

        @serializer.register
        class Marker(Serializable):
            def to_dict(self) -> dict[str, Any]:
                return {}

            @classmethod
            def from_dict(cls, data: dict[str, Any]) -> "Marker":
                return cls()

        self.assertIsInstance(serializer.loads('{"type": "Marker"}'), Marker)


class RoundTripTests(unittest.TestCase):
    def test_every_shape(self) -> None:
        serializer = make_serializer()
        for shape in (Circle(2), Rectangle(3, 4.5), Square(0.1),
                      Triangle(3, 4, 5)):
            with self.subTest(shape=shape):
                restored = serializer.loads(serializer.dumps(shape))
                self.assertEqual(restored, shape)
                self.assertIs(type(restored), type(shape))

    def test_random_drawings_keep_types_and_exact_values(self) -> None:
        serializer = make_serializer()
        rng = random.Random(4)
        for _ in range(200):
            drawing = Drawing(random_shape(rng)
                              for _ in range(rng.randint(0, 8)))
            restored = serializer.loads(serializer.dumps(drawing))
            self.assertEqual(restored, drawing)
            # repr показывает и классы, и типы чисел: 2 и 2.0 различаются.
            self.assertEqual(repr(restored), repr(drawing))

    def test_json_layout(self) -> None:
        text = make_serializer().dumps(Drawing([Circle(2), Square(1.5)]))
        self.assertEqual(text, "\n".join([
            "{",
            '  "type": "Drawing",',
            '  "shapes": [',
            "    {",
            '      "type": "Circle",',
            '      "radius": 2',
            "    },",
            "    {",
            '      "type": "Square",',
            '      "side": 1.5',
            "    }",
            "  ]",
            "}",
        ]))

    def test_other_classes_and_plain_values(self) -> None:
        serializer = JsonSerializer([Point])
        value = [Point(1, 2, "начало"), None, True, 1.5, "текст"]
        text = serializer.dumps(value)
        self.assertIn("начало", text)  # ensure_ascii=False
        self.assertEqual(serializer.loads(text), value)
        self.assertEqual(serializer.loads("5"), 5)

    def test_tuple_becomes_list(self) -> None:
        serializer = JsonSerializer()
        self.assertEqual(serializer.loads(serializer.dumps((1, 2))), [1, 2])


class DumpErrorTests(unittest.TestCase):
    def test_unregistered_class(self) -> None:
        serializer = JsonSerializer([Circle])
        with self.assertRaisesRegex(SerializationError,
                                    "^Класс Square не зарегистрирован$"):
            serializer.dumps(Square(1))

    def test_values_that_json_cannot_hold(self) -> None:
        serializer = JsonSerializer([Holder])
        for bad in (float("nan"), float("inf"), object(), {"a": 1}, {1},
                    1j, 10**5000):
            with self.subTest(bad=bad):
                with self.assertRaises(SerializationError):
                    serializer.dumps(Holder(bad))

    def test_error_names_the_place(self) -> None:
        serializer = JsonSerializer([Holder])
        with self.assertRaisesRegex(SerializationError,
                                    r"^value\[1\]\.value: число nan"):
            serializer.dumps(Holder([1, Holder(float("nan"))]))

    def test_type_field_is_reserved(self) -> None:
        serializer = JsonSerializer([Holder])

        class Typed(Holder):
            def to_dict(self) -> dict[str, Any]:
                return {"type": "подмена"}

        serializer.register(Typed)
        with self.assertRaisesRegex(SerializationError, "занято"):
            serializer.dumps(Typed(1))


class LoadErrorTests(unittest.TestCase):
    def assert_load_error(self, text: str, message: str) -> None:
        with self.assertRaises(SerializationError) as caught:
            make_serializer().loads(text)
        self.assertIn(message, str(caught.exception))

    def test_broken_json(self) -> None:
        self.assert_load_error('{"type": "Circle",}',
                               "Некорректный JSON: ")
        self.assert_load_error("", "строка 1, столбец 1")

    def test_non_standard_constants(self) -> None:
        # json.loads('NaN') по умолчанию вернул бы float('nan').
        self.assertNotEqual(json.loads("NaN"), json.loads("NaN"))
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                self.assert_load_error(
                    f'{{"type": "Circle", "radius": {constant}}}',
                    f"{constant} — не число",
                )

    def test_number_too_big_for_float(self) -> None:
        self.assert_load_error('{"type": "Circle", "radius": 1e400}',
                               "1e400 больше 1e308")
        self.assert_load_error("1" * 5000, "Некорректный JSON")

    def test_duplicate_keys(self) -> None:
        # Обычный json.loads молча взял бы последнее значение.
        self.assert_load_error(
            '{"type": "Circle", "radius": 1, "radius": -1}',
            "Поле «radius» повторяется",
        )

    def test_type_problems(self) -> None:
        self.assert_load_error('{"radius": 1}', "нет поля «type»")
        self.assert_load_error('{"type": 5, "radius": 1}', "нет поля «type»")
        self.assert_load_error('{"type": "Hexagon", "side": 1}',
                               "Неизвестный тип «Hexagon»")
        self.assert_load_error('{"type": "Shape"}', "Неизвестный тип")

    def test_field_problems(self) -> None:
        self.assert_load_error('{"type": "Circle"}',
                               "Circle: нет поля «radius»")
        self.assert_load_error('{"type": "Circle", "radius": 1, "r": 2}',
                               "Circle: лишнее поле «r»")
        self.assert_load_error('{"type": "Triangle", "a": 1, "b": 2, "c": 3}',
                               "треугольник не построить")

    def test_values_are_checked_by_constructors(self) -> None:
        for value in ("-1", "0", "true", '"2"', "null", "[2]"):
            with self.subTest(value=value):
                self.assert_load_error(
                    f'{{"type": "Circle", "radius": {value}}}', "Радиус: "
                )

    def test_drawing_problems(self) -> None:
        self.assert_load_error('{"type": "Drawing", "shapes": 5}',
                               "должно быть списком")
        self.assert_load_error(
            '{"type": "Drawing", "shapes": [{"type": "Drawing", '
            '"shapes": []}]}',
            "только фигуры",
        )
        self.assert_load_error('{"type": "Drawing", "shapes": [1]}',
                               "только фигуры")

    def test_nested_error_shows_path(self) -> None:
        self.assert_load_error(
            '{"type": "Drawing", "shapes": [{"type": "Square", "side": 1},'
            ' {"type": "Circle", "radius": -2}]}',
            "shapes[1] (Circle): Радиус: нужно число больше нуля, "
            "получено -2",
        )

    def test_expected_type(self) -> None:
        serializer = make_serializer()
        text = serializer.dumps(Circle(1))
        self.assertEqual(serializer.loads(text, Shape), Circle(1))
        with self.assertRaisesRegex(
            SerializationError, "Ожидался объект Drawing, а в JSON — Circle"
        ):
            serializer.loads(text, Drawing)
        with self.assertRaisesRegex(SerializationError, "— list"):
            serializer.loads("[]", Drawing)

    def test_deep_nesting_is_an_error_not_a_crash(self) -> None:
        self.assert_load_error("[" * 100_000 + "]" * 100_000,
                               "Слишком глубокая вложенность")

    def test_error_is_a_value_error(self) -> None:
        self.assertTrue(issubclass(SerializationError, ValueError))


class FileTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.serializer = make_serializer()

    def test_save_and_load(self) -> None:
        path = self.directory / "чертёж.json"
        drawing = Drawing([Circle(2), Triangle(3, 4, 5)])
        self.serializer.save(drawing, path)
        self.assertTrue(path.read_bytes().endswith(b"}\n"))
        self.assertEqual(self.serializer.load(path, Drawing), drawing)

    def test_file_with_bom_is_accepted(self) -> None:
        # Блокнот Windows может сохранить UTF-8 с меткой BOM.
        path = self.directory / "bom.json"
        text = self.serializer.dumps(Square(3))
        path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        self.assertEqual(self.serializer.load(path), Square(3))

    def test_file_not_in_utf8(self) -> None:
        path = self.directory / "cp1251.json"
        path.write_bytes('{"type": "Круг"}'.encode("cp1251"))
        with self.assertRaisesRegex(SerializationError, "UTF-8"):
            self.serializer.load(path)

    def test_missing_file_is_os_error(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.serializer.load(self.directory / "нет.json")

    def test_failed_save_keeps_existing_file(self) -> None:
        path = self.directory / "old.json"
        self.serializer.save(Circle(1), path)
        before = path.read_text(encoding="utf-8")
        with self.assertRaises(SerializationError):
            JsonSerializer([Circle]).save(Drawing([Circle(2)]), path)
        self.assertEqual(path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
