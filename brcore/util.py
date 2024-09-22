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
