from typing import NamedTuple
import asyncio


class BackgroundTasks(set):
    """`runner`のバックグラウンド実行するタスクの管理をする集合"""
    def add(self, element: asyncio.Task) -> None:
        if type(element) is asyncio.Task:
            element.add_done_callback(self.discard)
            return super().add(element)
        else:
            raise TypeError("element is not asyncio.Task")

    def tasks_cancel(self) -> None:
        """タスク達をキャンセル"""
        for i in self:
            i.cancel()


class ExceptionTexts(NamedTuple):
    TYPE_INVALID = "type情報が不適です。"

    ID_ALREADY_RESERVED = "IDがすでに予約済みです。"
    ID_INVALID = "IDが不適です。"

    TYPE_AND_ID_ALREADY_RESERVED = "type情報とIDの組み合わせがすでに予約済みです。"
    TYPE_AND_ID_INVALID = "type情報とIDの組み合わせが不適です。"

    FUNCTION_NOT_COROUTINEFUNC = "関数がcoroutinefunctionではありません。"

    MAIN_FUNC_NOT_RUNNING = "メイン関数が実行されていません"

    DECO_ARG_INVALID = "引数が不正です。デコレーターの使い方を間違えている可能性があります。"
