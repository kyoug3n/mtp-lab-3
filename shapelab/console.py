"""Ввод и вывод для интерактивного меню.

Меню получает функции ввода и вывода параметрами (по умолчанию — встроенные
``input`` и ``print``). Поэтому его можно проверять тестами и показывать в
демонстрационных сессиях, подставляя заранее заданный ввод через
:class:`ScriptedConsole`.
"""
import math
from collections import deque
from collections.abc import Callable, Iterable

InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]

EXIT_WORD = "выход"


def read_line(prompt: str, input_func: InputFunc = input) -> str | None:
    """Прочитать строку без пробелов по краям.

    Возвращает ``None``, если ввод закончился (Ctrl+Z или Ctrl+D, Ctrl+C)
    или введено слово «выход» в любом регистре.
    """
    try:
        text = input_func(prompt)
    except (EOFError, KeyboardInterrupt):
        return None
    text = text.strip()
    if text.lower() == EXIT_WORD:
        return None
    return text


def parse_number(text: str) -> int | float | None:
    """Разобрать число: целое остаётся ``int``, дробная часть — через точку
    или запятую. Возвращает ``None``, если это не число.

    >>> parse_number("2"), parse_number("1,5"), parse_number("1e3")
    (2, 1.5, 1000.0)
    >>> parse_number("два") is None, parse_number("nan") is None
    (True, True)
    """
    text = text.strip().replace(",", ".")
    try:
        return int(text)
    except ValueError:
        pass
    try:
        value = float(text)
    except ValueError:
        return None
    return None if math.isnan(value) else value


def read_positive_number(
    prompt: str, input_func: InputFunc = input, output_func: OutputFunc = print
) -> int | float | None:
    """Запрашивать строку, пока не будет введено конечное число больше нуля.

    Возвращает ``None``, если пользователь завершил ввод (см.
    :func:`read_line`).
    """
    while True:
        text = read_line(prompt, input_func)
        if text is None:
            return None
        number = parse_number(text)
        if number is None:
            output_func("Нужно число, например 2 или 1,5.")
        elif number <= 0:
            output_func("Нужно число больше нуля.")
        elif number == math.inf:
            output_func("Слишком большое число.")
        else:
            return number


class ScriptedConsole:
    """Консоль с заранее заданным вводом — для тестов и демонстрации.

    В ``transcript`` записывается то, что увидел бы пользователь в терминале:
    приглашение вместе с «набранным» текстом и все выведенные строки.
    Когда заданный ввод заканчивается, ``input`` бросает ``EOFError``,
    как встроенная функция при конце ввода.
    """

    def __init__(self, lines: Iterable[str]) -> None:
        self._lines = deque(lines)
        self.transcript: list[str] = []

    def input(self, prompt: str) -> str:
        """Вернуть следующую заданную строку, записав её в протокол."""
        if not self._lines:
            self.transcript.append(prompt)
            raise EOFError
        line = self._lines.popleft()
        self.transcript.append(prompt + line)
        return line

    def print(self, text: str = "") -> None:
        """Записать выведенный текст в протокол."""
        self.transcript.append(text)

    @property
    def text(self) -> str:
        """Весь протокол одной строкой."""
        return "\n".join(self.transcript)
