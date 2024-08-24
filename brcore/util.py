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
    ID_ALREADY_RESERVED = "IDがすでに予約済みです。"
    ID_INVALID = "IDが不適です。"

    FUNCTION_NOT_COROUTINEFUNC = "関数がcoroutinefunctionではありません。"

    MAIN_FUNC_NOT_RUNNING = "メイン関数が実行されていません"

    DECO_ARG_NOT_STR = "引数がstrではありません。デコレーターの使い方を間違えている可能性があります。"
