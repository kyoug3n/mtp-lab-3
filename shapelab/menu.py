"""Интерактивное меню: чертёж из фигур, запись в JSON и чтение из него.

Меню собирает вместе все классы варианта: фигуры создаются по введённым
размерам (конструкторы проверяют их, треугольник — статическим методом
``is_valid``), чертёж выводится обходом через класс-итератор, а сохраняется
и загружается сериализатором.

Меню ничего не знает о конкретных фигурах: список видов, подписи размеров
и порядок вопросов берутся из ``SHAPE_CLASSES`` и атрибута ``SIZE_LABELS``
каждого класса. Новая фигура появится в меню, если добавить её класс в
этот список.
"""
from collections.abc import Callable
from pathlib import Path

from shapelab.console import (
    InputFunc,
    OutputFunc,
    read_line,
    read_positive_number,
)
from shapelab.drawing import Drawing
from shapelab.serializer import JsonSerializer, SerializationError
from shapelab.shapes import (
    Circle,
    Number,
    Rectangle,
    Shape,
    Square,
    Triangle,
    format_number,
)

TITLE = "Лабораторная работа №3 «Объектно-ориентированное программирование»"

SHAPE_CLASSES: list[type[Shape]] = [Circle, Rectangle, Square, Triangle]

SERIALIZER = JsonSerializer([*SHAPE_CLASSES, Drawing])

DEFAULT_FILE = "drawing.json"


class ShapeMenu:
    """Диалог с пользователем вокруг одного чертежа.

    :param directory: папка, относительно которой понимаются имена файлов
        (по умолчанию — текущая).
    """

    def __init__(
        self,
        input_func: InputFunc = input,
        output_func: OutputFunc = print,
        directory: Path | None = None,
    ) -> None:
        self._input = input_func
        self._output = output_func
        self._directory = directory if directory is not None else Path()
        self.drawing = Drawing()
        # Пункты меню: название и метод, который его выполняет.
        self._items: list[tuple[str, Callable[[], None]]] = [
            ("Добавить фигуру", self.add_shape),
            ("Показать чертёж", self.show_drawing),
            ("Сохранить чертёж в JSON", self.save),
            ("Загрузить чертёж из JSON", self.load),
        ]

    def run(self) -> None:
        """Показывать меню и выполнять пункты до выхода."""
        self._output(TITLE)
        while True:
            self._output("")
            self._output("Выберите действие:")
            for number, (title, _) in enumerate(self._items, start=1):
                self._output(f"  {number}. {title}")
            self._output("  0. Выход")
            choice = read_line("Номер: ", self._input)
            if choice is None or choice == "0":
                self._output("До свидания!")
                return
            item = self._choose(choice, len(self._items))
            if item is None:
                self._output(f"Нет такого пункта: {choice!r}.")
                continue
            title, action = self._items[item]
            self._output(f"--- {title} ---")
            action()

    def add_shape(self) -> None:
        """Спросить вид и размеры фигуры и добавить её на чертёж."""
        cls = self._ask_shape_class()
        if cls is None:
            return
        sizes: dict[str, Number] = {}
        for name, label in cls.SIZE_LABELS.items():
            value = read_positive_number(
                f"{label.capitalize()}: ", self._input, self._output
            )
            if value is None:
                return
            sizes[name] = value
        try:
            shape = cls(**sizes)
        except ValueError as error:
            self._output(f"Фигура не добавлена. {error}.")
            return
        self.drawing.add(shape)
        self._output(f"Добавлено: {shape.describe()}")

    def show_drawing(self) -> None:
        """Вывести фигуры чертежа, их площади и периметры."""
        if not len(self.drawing):
            self._output("На чертеже нет фигур.")
            return
        self._output(f"Фигур на чертеже: {len(self.drawing)}")
        for number, shape in enumerate(self.drawing, start=1):
            self._output(f"  {number}. {shape.describe()}")
        self._output(
            f"Общая площадь: {format_number(self.drawing.total_area())}"
        )

    def save(self) -> None:
        """Записать чертёж в JSON-файл."""
        name = self._ask_file_name()
        if name is None:
            return
        try:
            SERIALIZER.save(self.drawing, self._directory / name)
        except (OSError, SerializationError) as error:
            self._output(f"Не удалось сохранить {name}: {_reason(error)}.")
            return
        self._output(f"Чертёж сохранён в {name} (фигур: {len(self.drawing)}).")

    def load(self) -> None:
        """Заменить чертёж загруженным из JSON-файла."""
        name = self._ask_file_name()
        if name is None:
            return
        try:
            drawing = SERIALIZER.load(self._directory / name, Drawing)
        except FileNotFoundError:
            self._output(f"Файл не найден: {name}.")
            return
        except (OSError, SerializationError) as error:
            self._output(f"Не удалось загрузить {name}: {_reason(error)}.")
            return
        self.drawing = drawing
        self._output(f"Чертёж загружен из {name} (фигур: {len(drawing)}).")

    def _ask_shape_class(self) -> type[Shape] | None:
        self._output("Вид фигуры:")
        for number, cls in enumerate(SHAPE_CLASSES, start=1):
            self._output(f"  {number}. {cls.NAME.capitalize()}")
        while True:
            choice = read_line("Номер: ", self._input)
            if choice is None:
                return None
            item = self._choose(choice, len(SHAPE_CLASSES))
            if item is not None:
                return SHAPE_CLASSES[item]
            self._output(f"Нет такого вида: {choice!r}.")

    def _ask_file_name(self) -> str | None:
        name = read_line(f"Файл (Enter — {DEFAULT_FILE}): ", self._input)
        if name is None:
            return None
        return name or DEFAULT_FILE

    @staticmethod
    def _choose(choice: str, count: int) -> int | None:
        """Индекс пункта по введённому номеру от 1 до ``count``."""
        numbers = [str(number) for number in range(1, count + 1)]
        return numbers.index(choice) if choice in numbers else None


def _reason(error: Exception) -> str:
    """Причина ошибки для пользователя без технических подробностей."""
    if isinstance(error, OSError) and error.strerror:
        return error.strerror
    return str(error)


def main(
    input_func: InputFunc = input, output_func: OutputFunc = print
) -> None:
    """Запустить меню в текущей папке."""
    ShapeMenu(input_func, output_func).run()


if __name__ == "__main__":
    main()
