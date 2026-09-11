"""Примеры из документации модулей выполняются как тесты (doctest)."""
import doctest
import unittest

from shapelab import drawing, serializer, shapes

MODULES = [shapes, drawing, serializer]


def load_tests(
    loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str
) -> unittest.TestSuite:
    for module in MODULES:
        tests.addTests(doctest.DocTestSuite(module))
    return tests
