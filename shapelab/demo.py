"""Демонстрационные сессии меню с заранее заданным вводом.

Запуск: ``python -m shapelab.demo reports/demo.txt`` (без аргумента протокол
печатается на экран). Каждая сессия — отдельный запуск меню
``python -m shapelab``; ввод подставляется через
:class:`shapelab.console.ScriptedConsole` и виден после приглашений, как в
терминале. Все сессии работают в одной временной папке: файл, сохранённый в
первой, загружается во второй. Содержимое JSON-файлов показано в протоколе.
"""
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

from shapelab.console import ScriptedConsole
from shapelab.menu import ShapeMenu


class Session(NamedTuple):
    """Запуск меню: заголовок, ввод, файлы до запуска и файлы после."""

    title: str
    user_input: list[str]
    files_before: dict[str, str]
    files_after: list[str]


BROKEN_FILES = {
    "broken.json": '{"type": "Drawing", "shapes": [',
    "nan.json": '{"type": "Drawing", "shapes": '
                '[{"type": "Circle", "radius": NaN}]}',
    "negative.json": '{"type": "Drawing", "shapes": [{"type": "Square", '
                     '"side": 1}, {"type": "Circle", "radius": -2}]}',
    "hexagon.json": '{"type": "Drawing", "shapes": '
                    '[{"type": "Hexagon", "side": 1}]}',
    "twice.json": '{"type": "Circle", "radius": 1, "radius": 2}',
    "circle.json": '{"type": "Circle", "radius": 1}',
}

SESSIONS = [
    Session(
        "Построение чертежа и сохранение: python -m shapelab",
        [
            "1", "1", "-2", "abc", "2",        # круг: ошибки ввода, затем 2
            "1", "2", "3", "4,5",              # прямоугольник 3 × 4,5
            "1", "5", "3", "0.5",              # вид 5 не существует; квадрат
            "1", "4", "1", "2", "10",          # треугольник не построить
            "1", "4", "3", "4", "5",           # треугольник 3-4-5
            "2",
            "3", "",                           # сохранить в drawing.json
            "0",
        ],
        {},
        ["drawing.json"],
    ),
    Session(
        "Загрузка в новом запуске: python -m shapelab",
        ["2", "4", "", "2", "0"],
        {},
        [],
    ),
    Session(
        "Ошибки в файлах: python -m shapelab",
        [
            "4", "broken.json", "4", "nan.json", "4", "negative.json",
            "4", "hexagon.json", "4", "twice.json", "4", "circle.json",
            "4", "нет.json", "выход",
        ],
        BROKEN_FILES,
        [],
    ),
]


def git_revision() -> str:
    """Короткий хеш и дата текущего коммита (с пометкой о правках)."""
    try:
        revision = subprocess.run(
            ["git", "log", "-1", "--format=%h (%ci)"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "неизвестна (git недоступен)"
    if status:
        revision += " + незакоммиченные изменения"
    return revision


def show_file(path: Path) -> list[str]:
    """Строки протокола с содержимым файла."""
    text = path.read_text(encoding="utf-8")
    return [f"--- файл {path.name} ---", *text.splitlines()]


def build_sessions() -> list[str]:
    """Выполнить все сессии и вернуть их протокол построчно.

    Каждая сессия начинается с пустой строки — по первой пустой строке
    протокол делится на штамп и сессии.
    """
    lines: list[str] = []
    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        for number, session in enumerate(SESSIONS, start=1):
            lines += ["", f"=== {number}. {session.title} ==="]
            for file_name, text in session.files_before.items():
                path = directory / file_name
                path.write_text(text + "\n", encoding="utf-8", newline="\n")
                lines += show_file(path)
            if session.files_before:
                lines.append("--- запуск меню ---")
            console = ScriptedConsole(session.user_input)
            ShapeMenu(console.input, console.print, directory).run()
            lines += console.transcript
            for file_name in session.files_after:
                lines += show_file(directory / file_name)
    return lines


def build_header() -> list[str]:
    """Штамп протокола: команда, ревизия и версия Python (без пустых строк)."""
    return [
        "Демонстрационные сессии лабораторной работы №3 (вариант 4)",
        "Команда: python -m shapelab.demo reports/demo.txt",
        f"Ревизия: {git_revision()}",
        f"Python: {platform.python_version()}",
        "Ввод пользователя задан заранее и показан после приглашений.",
        "Все сессии работают в одной временной папке.",
    ]


def build_report() -> str:
    """Полный протокол: штамп и все сессии."""
    return "\n".join(build_header() + build_sessions()) + "\n"


def main_demo(argv: list[str]) -> None:
    """Записать протокол в файл из ``argv`` или вывести его на экран."""
    report = build_report()
    if argv:
        Path(argv[0]).write_text(report, encoding="utf-8", newline="\n")
        print(f"Протокол записан в {argv[0]}")
    else:
        print(report, end="")


if __name__ == "__main__":
    main_demo(sys.argv[1:])
