from typing import NamedTuple


class ExceptionTexts(NamedTuple):
    TYPE_INVALID = "type情報が不適です。"

    ID_ALREADY_RESERVED = "IDがすでに予約済みです。"
    ID_INVALID = "IDが不適です。"

    TYPE_AND_ID_ALREADY_RESERVED = "type情報とIDの組み合わせがすでに予約済みです。"
    TYPE_AND_ID_INVALID = "type情報とIDの組み合わせが不適です。"

    FUNCTION_NOT_COROUTINEFUNC = "関数がcoroutinefunctionではありません。"

    MAIN_FUNC_NOT_RUNNING = "メイン関数が実行されていません"

    DECO_ARG_INVALID = "引数が不正です。デコレーターの使い方を間違えている可能性があります。"
