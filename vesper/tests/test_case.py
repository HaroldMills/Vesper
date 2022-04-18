"""Module containing unit test test case superclass."""


import unittest

from vesper.tests.test_case_mixin import TestCaseMixin


class TestCase(unittest.TestCase, TestCaseMixin):
    pass
