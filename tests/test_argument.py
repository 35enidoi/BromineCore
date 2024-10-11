from unittest import TestCase
from brcore import Bromine
from brcore.enum import ExceptionTexts


class DecoreterTest(TestCase):
    def setUp(self) -> None:
        self.br = Bromine("hogeinstance", "hogehoge")

    def test_comeback_deco_incorrect_use(self):
        with self.assertRaises(TypeError) as mes:
            self.br.add_comeback_deco(lambda _: _)

        self.assertEqual(str(mes.exception), ExceptionTexts.DECO_ARG_INVALID)

    def test_ws_connect_deco_incorrect_use(self):
        with self.assertRaises(TypeError) as mes:
            self.br.ws_connect_deco(lambda _: _)

        self.assertEqual(str(mes.exception), ExceptionTexts.DECO_ARG_INVALID)

    def test_ws_subnote_deco_incorrect_use(self):
        with self.assertRaises(TypeError) as mes:
            self.br.ws_subnote_deco(lambda _: _)

        self.assertEqual(str(mes.exception), ExceptionTexts.DECO_ARG_INVALID)


class ArgNotCoroutineFunctionTest(TestCase):
    def setUp(self) -> None:
        self.br = Bromine("hogeinstance", "hogehoge")

    def test_add_comeback_not_coroutinefunction(self):
        with self.assertRaises(TypeError) as mes:
            self.br.add_comeback(lambda _: _)

        self.assertEqual(str(mes.exception), ExceptionTexts.FUNCTION_NOT_COROUTINEFUNC)

    def test_add_ws_type_id_not_coroutinefunction(self):
        with self.assertRaises(TypeError) as mes:
            self.br.add_ws_type_id("hoge", "hoga", lambda _: _)

        self.assertEqual(str(mes.exception), ExceptionTexts.FUNCTION_NOT_COROUTINEFUNC)

    def test_except_info_func_assign_not_coroutinefunction(self):
        with self.assertRaises(TypeError) as mes:
            self.br.expect_info_func = lambda _: _

        self.assertEqual(str(mes.exception), ExceptionTexts.FUNCTION_NOT_COROUTINEFUNC)
