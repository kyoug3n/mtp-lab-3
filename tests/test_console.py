"""Тесты функций ввода и подставной консоли."""
import unittest

from shapelab.console import (
    ScriptedConsole,
    parse_number,
    read_line,
    read_positive_number,
)


class ReadLineTests(unittest.TestCase):
    def test_strips_spaces(self) -> None:
        console = ScriptedConsole(["  42  "])
        self.assertEqual(read_line("> ", console.input), "42")

    def test_exit_word_in_any_case(self) -> None:
        for word in ("выход", "ВЫХОД", "  Выход "):
            with self.subTest(word=word):
                console = ScriptedConsole([word])
                self.assertIsNone(read_line("> ", console.input))

    def test_end_of_input(self) -> None:
        console = ScriptedConsole([])
        self.assertIsNone(read_line("> ", console.input))

    def test_keyboard_interrupt(self) -> None:
        def interrupted(prompt: str) -> str:
            raise KeyboardInterrupt

        self.assertIsNone(read_line("> ", interrupted))


class ParseNumberTests(unittest.TestCase):
    def test_integers_stay_integers(self) -> None:
        for text, expected in (("2", 2), (" -7 ", -7), ("1_000", 1000)):
            with self.subTest(text=text):
                number = parse_number(text)
                self.assertEqual(number, expected)
                self.assertIsInstance(number, int)

    def test_fractions_with_point_or_comma(self) -> None:
        for text, expected in (("1.5", 1.5), ("1,5", 1.5), (".5", 0.5),
                               ("2e-3", 0.002), ("1e3", 1000.0)):
            with self.subTest(text=text):
                number = parse_number(text)
                self.assertEqual(number, expected)
                self.assertIsInstance(number, float)

    def test_not_numbers(self) -> None:
        for text in ("", "два", "1.2.3", "2 3", "nan", "NaN", "0x10"):
            with self.subTest(text=text):
                self.assertIsNone(parse_number(text))


class ReadPositiveNumberTests(unittest.TestCase):
    def test_repeats_until_positive_number(self) -> None:
        console = ScriptedConsole(["abc", "0", "-1", "1e400", "2,5"])
        number = read_positive_number("> ", console.input, console.print)
        self.assertEqual(number, 2.5)
        self.assertEqual(console.transcript, [
            "> abc",
            "Нужно число, например 2 или 1,5.",
            "> 0",
            "Нужно число больше нуля.",
            "> -1",
            "Нужно число больше нуля.",
            "> 1e400",
            "Слишком большое число.",
            "> 2,5",
        ])

    def test_exit(self) -> None:
        console = ScriptedConsole(["abc", "выход"])
        self.assertIsNone(
            read_positive_number("> ", console.input, console.print)
        )


class ScriptedConsoleTests(unittest.TestCase):
    def test_transcript_shows_prompt_with_typed_text(self) -> None:
        console = ScriptedConsole(["да"])
        console.print("Вопрос?")
        console.input("Ответ: ")
        self.assertEqual(console.text, "Вопрос?\nОтвет: да")

    def test_raises_eof_when_lines_run_out(self) -> None:
        console = ScriptedConsole([])
        with self.assertRaises(EOFError):
            console.input("> ")


if __name__ == "__main__":
    unittest.main()
