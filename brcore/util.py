from typing import NamedTuple


class ExceptionTexts(NamedTuple):
    ID_ALREADY_RESERVED = "IDがすでに予約済みです。"
    ID_INVALID = "IDが不適です。"

    FUNCTION_NOT_COROUTINEFUNC = "関数がcoroutinefunctionではありません。"

    MAIN_FUNC_NOT_RUNNING = "メイン関数が実行されていません"

    DECO_ARG_NOT_STR = "引数がstrではありません。デコレーターの使い方を間違えている可能性があります。"
