from enum import StrEnum


class ExceptionTexts(StrEnum):
    ID_ALREADY_RESERVED = "IDがすでに予約済みです。"
    ID_INVALID = "IDが不適です。"

    FUNCTION_NOT_COROUTINEFUNC = "関数がcoroutinefunctionではありません。"

    MAIN_FUNC_NOT_RUNNING = "メイン関数が実行されていません"