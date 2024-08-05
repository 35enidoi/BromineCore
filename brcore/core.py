import json
import asyncio
import uuid
import logging
from functools import partial
from typing import Any, Callable, NoReturn, Optional, Union, Coroutine

import websockets


__all__ = ["Bromine"]


class _BackgroundTasks(set):
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


class Bromine:
    """misskeyのwebsocketAPIを使いやすくしたクラス

    websocketの実装を一々作らなくても簡単にwebsocketの通信ができるようになります

    Parameters
    ----------
    instance: str
        インスタンス名
    token: :obj:`str`, optional
        トークン"""

    def __init__(self, instance: str, token: Optional[str] = None) -> None:
        self.__COOL_TIME = 5

        # 値を保持するキューとか
        # uuid:[channelname, awaitablefunc, params]
        self.__channels: dict[str, tuple[str, Callable[[dict[str, Any]], Coroutine[Any, Any, None]], dict[str, Any]]] = {}
        # uuid:tuple[isblock, awaitablefunc]
        self.__on_comebacks: dict[str, tuple[bool, Callable[[], Coroutine[Any, Any, None]]]] = {}
        # send_queueはここで作るとエラーが出るので型ヒントのみ
        self.__send_queue: asyncio.Queue[tuple[str, dict]]

        # 実行中かどうかの変数
        self.__is_running: bool = False

        # websocketのURL
        if token is not None:
            self.__WS_URL = f'wss://{instance}/streaming?i={token}'
        else:
            # トークンがないときはパラメーターを消しとく
            self.__WS_URL = f'wss://{instance}/streaming'

        # logger作成
        self.__logger = logging.getLogger("Bromine")
        # logを簡単にできるよう部分適用する
        self.__log = partial(self.__logger.log, logging.DEBUG)

    @property
    def loglevel(self) -> int:
        """現在のログレベル"""
        return self.__log.args[0]

    @loglevel.setter
    def loglevel(self, level: int) -> None:
        self.__log = partial(self.__logger.log, level)

    @property
    def cooltime(self) -> int:
        """websocketの接続が切れた時に再接続まで待つ時間"""
        return self.__COOL_TIME

    @cooltime.setter
    def cooltime(self, time: int) -> None:
        if time > 0:
            self.__COOL_TIME = time
        else:
            ValueError("負の値です")

    @property
    def is_running(self) -> bool:
        """メイン関数が実行中かどうか"""
        return self.__is_running

    async def main(self) -> NoReturn:
        """開始する関数"""
        self.__log("start main.")
        # send_queueをinitで作るとattached to a different loopとかいうゴミでるのでここで宣言
        self.__send_queue = asyncio.Queue()
        self.__is_running = True
        # バックグラウンドタスクの集合
        backgrounds = _BackgroundTasks()
        try:
            await asyncio.create_task(self.__runner(backgrounds))
        finally:
            backgrounds.tasks_cancel()
            self.__is_running = False
            self.__log("finish main.")

    async def __runner(self, background_tasks: _BackgroundTasks) -> NoReturn:
        """websocketとの交信を行うメインdaemon"""
        # 何回連続で接続に失敗したかのカウンター
        connect_fail_count = 0
        # この変数たちは最初に接続失敗すると未定義になるから保険のため
        # websocket_daemon(__ws_send_d)
        wsd: Union[None, asyncio.Task] = None
        # comebacks(asyncio.gather)
        comebacks: Union[None, asyncio.Future] = None
        while True:
            try:
                async with websockets.connect(self.__WS_URL) as ws:
                    # ちゃんと通ってるかpingで確認
                    ping_wait = await ws.ping()
                    pong_latency = await ping_wait
                    self.__log(f"websocket connect success. latency: {pong_latency}s")

                    # 送るdaemonの作成
                    wsd = asyncio.create_task(self.__ws_send_d(ws))

                    # comebacksの処理
                    cmbs: list[Coroutine[Any, Any, None]] = []
                    for i in self.__on_comebacks.values():
                        if i[0]:
                            # もしブロックしなければいけないcomebackなら待つ
                            await i[1]()
                        else:
                            # でなければ後で処理する
                            cmbs.append(i[1]())
                    if cmbs != []:
                        # 全部一気にgatherで管理
                        comebacks = asyncio.gather(*cmbs, return_exceptions=True)

                    # 接続に成功したということでfail_countを0に
                    connect_fail_count = 0
                    while True:
                        # データ受け取り
                        data = json.loads(await ws.recv())
                        if data['type'] == 'channel':
                            for i, v in self.__channels.items():
                                if data["body"]["id"] == i:
                                    background_tasks.add(asyncio.create_task(v[1](data["body"])))
                                    break
                            else:
                                self.__log("data come from unknown channel")
                        else:
                            # たまにchannel以外から来ることがある（謎）
                            self.__log(f"data come from not channel, datatype[{data['type']}]")

            except (
                asyncio.exceptions.TimeoutError,
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
            ) as e:
                # websocketが死んだりタイムアウトした時の処理
                self.__log(f"error occured:{e}")
                connect_fail_count += 1
                await asyncio.sleep(self.__COOL_TIME)
                if connect_fail_count > 5:
                    # Todo: 例外を投げる？
                    # 5回以上連続で失敗したとき長く寝るようにする
                    # とりあえず30待つようにする
                    await asyncio.sleep(30)

            except Exception as e:
                # 予定外のエラー発生時。
                self.__log(f"fatal Error:{type(e)}, args:{e.args}")
                raise e

            finally:
                # 再接続する際、いろいろ初期化する
                if type(wsd) is asyncio.Task:
                    # __ws_send_dを止める
                    wsd.cancel()
                    try:
                        await wsd
                    except asyncio.CancelledError:
                        pass
                    wsd = None
                if comebacks is not None:
                    # ブロックしないcomebacksがもし生きていたら殺す
                    comebacks.cancel()
                    try:
                        await comebacks
                    except asyncio.CancelledError:
                        pass
                    comebacks = None

    def add_comeback(self,
                     func: Callable[[], Coroutine[Any, Any, None]],
                     block: bool = False,
                     id: Optional[str] = None) -> str:
        """comebackを作る関数

        Parameters
        ----------
        func: CoroutineFunction
            comeback時に実行する非同期関数
        block: bool
            websocketとの交信をブロッキングして実行するか
        id: :obj:`str`, optional
            識別id、ない場合自動生成される

        Returns
        -------
        str
            識別id

        Raises
        ------
        ValueError
            非同期関数funcがcoroutinefunctionでない時

        Note
        ----
        返り値の識別idはdel_comebackで使用します"""
        if id is None:
            # もしIDがない時生成する
            id = uuid.uuid4()
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("非同期関数funcがcoroutinefunctionではありません。")
        self.__on_comebacks[id] = (block, func)
        return id

    def del_comeback(self, id: str) -> None:
        """comeback消すやつ

        Parameter
        ---------
        id: str
            識別id

        Raises
        ------
        KeyError
            識別idが不適のとき"""
        self.__on_comebacks.pop(id)

    async def __ws_send_d(self, ws: websockets.WebSocketClientProtocol) -> NoReturn:
        """websocketを送るdaemon"""
        # すでに接続済みのchannelにconnectしたりしないようにするやつ
        already_connected_ids: set[str] = set()
        # まずはchannelsの再接続から始める
        for i, v in self.__channels.items():
            already_connected_ids.add(i)
            await ws.send(json.dumps({
                "type": "connect",
                "body": {
                    "channel": v[0],
                    "id": i,
                    "params": v[2]
                }
            }))

        # queueの初期化
        while not self.__send_queue.empty():
            type_, body_ = await self.__send_queue.get()
            if type_ == "connect":
                if body_["id"] in already_connected_ids:
                    # もうすでに送ったやつなので送らない
                    continue
                else:
                    # 追加する
                    already_connected_ids.add(body_["id"])

            await ws.send(json.dumps({
                "type": type_,
                "body": body_
            }))

        # あとはずっとqueueからgetしてそれを送る。
        while True:
            type_, body_ = await self.__send_queue.get()
            await ws.send(json.dumps({
                "type": type_,
                "body": body_
            }))

    def ws_send(self, type: str, body: dict[str, Any]) -> None:
        """ウェブソケットへ送るキューに情報を追加するやつ

        Parameters
        ----------
        type: str
            type情報
        body: dict[str, Any]
            body情報"""
        self.__send_queue.put_nowait((type, body))

    def ws_connect(self,
                   channel: str,
                   func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
                   id: Optional[str] = None,
                   **params: Any) -> str:
        """channelに接続する関数

        Parameters
        ----------
        channel: str
            チャンネル名
        func: CoroutineFunction
            反応があった時に実行される非同期関数
        id: :obj:`str`, optional
            識別id、もし指定されていない場合、自動生成される
        **params: Any
            接続する際のパラメーター

        Returns
        -------
        str
            識別id

        Raises
        -------
        ValueError
            非同期関数funcがcoroutinefunctionでない時

        Note
        ----
        返り値の識別idはws_disconnectで使用します"""
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("非同期関数funcがcoroutinefunctionではありません。")
        if id is None:
            # idがなかったら自動生成
            id = str(uuid.uuid4())
        # channelsに追加
        self.__channels[id] = (channel, func, params)
        body = {
            "channel": channel,
            "id": id,
            "params": params
        }
        if self.__is_running:
            # もしsend_queueがある時(実行中の時)
            self.ws_send("connect", body)
            self.__log(f"connect channel: {channel}, id: {id}")
        else:
            # ない時(実行前)
            self.__log(f"connect channel before run: {channel}, id: {id}")
        return id

    def ws_disconnect(self, id: str) -> None:
        """チャンネルを接続解除する関数

        Parameters
        ----------
        id: str
            識別id

        Raises
        ------
        KeyError
            識別idが不適のとき"""
        channel = self.__channels.pop(id)[0]
        body = {"id": id}
        self.ws_send("disconnect", body)
        self.__log(f"disconnect channel: {channel}, id: {id}")
