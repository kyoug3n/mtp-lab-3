"""Тесты демонстрационного протокола reports/demo.txt."""
import tempfile
import unittest
from pathlib import Path

from shapelab.demo import SESSIONS, build_sessions

REPORT = Path(__file__).resolve().parent.parent / "reports" / "demo.txt"


class DemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = build_sessions()

    def test_all_sessions_are_present(self) -> None:
        for number, session in enumerate(SESSIONS, start=1):
            self.assertIn(f"=== {number}. {session.title} ===", self.lines)

    def test_file_saved_in_first_session_is_loaded_in_second(self) -> None:
        self.assertIn("Чертёж сохранён в drawing.json (фигур: 4).",
                      self.lines)
        self.assertIn("Чертёж загружен из drawing.json (фигур: 4).",
                      self.lines)

    def test_every_broken_file_is_rejected(self) -> None:
        for name in SESSIONS[2].files_before:
            with self.subTest(name=name):
                self.assertTrue(any(
                    line.startswith(f"Не удалось загрузить {name}: ")
                    for line in self.lines
                ))

    def test_protocol_does_not_depend_on_machine(self) -> None:
        # Временная папка меняется от запуска к запуску и в протокол
        # попадать не должна.
        temp = str(Path(tempfile.gettempdir()))
        self.assertFalse(any(temp in line for line in self.lines))

    def test_committed_report_is_up_to_date(self) -> None:
        """Протокол в репозитории совпадает со свежим прогоном сессий.

        Штамп в начале файла (команда, ревизия, версия Python) не
        сравнивается: он описывает, где и когда протокол был получен.
        Штамп отделён от сессий первой пустой строкой, поэтому для сверки
        не нужен ни git, ни повторное построение штампа.
        """
        committed = REPORT.read_text(encoding="utf-8").splitlines()
        sessions = committed[committed.index(""):]
        self.assertEqual(
            sessions,
            self.lines,
            "reports/demo.txt устарел — выполните "
            "python -m shapelab.demo reports/demo.txt",
        )


if __name__ == "__main__":
    unittest.main()
