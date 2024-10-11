import json
import asyncio
import uuid
import logging
from functools import partial
from typing import Any, Callable, NoReturn, Optional, Union, Coroutine
from typing_extensions import deprecated

import websockets

from brcore.util import (
    BackgroundTasks
)
from brcore.enum import (
    ExceptionTexts
)


__all__ = ["Bromine"]


class Bromine:
    """misskeyのwebsocketAPIを使いやすくしたクラス

    websocketの実装を一々作らなくても簡単にwebsocketの通信ができるようになります

    Parameters
    ----------
    instance: str
        インスタンス名
    token: :obj:`str`, optional
        トークン
    secure_connect: :obj:`bool`, default True
        セキュアな接続をするかどうか

        これはローカルで構築したインスタンス等セキュアな接続が
        不可能な場所で使うもので通常は切る必要がありません。"""

    def __init__(self, instance: str, token: Optional[str] = None, *, secure_connect: bool = True) -> None:
        self.__COOL_TIME = 5

        # 値を保持するキューとか
        # uuid:tuple[isblock, coroutinefunc]
        self.__on_comebacks: dict[str, tuple[bool, Callable[[], Coroutine[Any, Any, None]]]] = {}
        # send_queueはここで作るとエラーが出るので型ヒントのみ
        self.__send_queue: asyncio.Queue[tuple[str, dict]]
        # type: dict[id, coroutinefunc]
        self.__ws_type_id_dict: dict[str, dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, None]]]] = {}
        # tuple[type, id]: body
        self.__ws_on_comebacks: dict[tuple[str, str], dict[str, Any]] = {}

        # 実行中かどうかの変数
        self.__is_running: bool = False
        # 謎の場所からくる情報受取関数
        self.__expect_info_func: Optional[Callable[[dict[str, Any]], Coroutine[Any, Any, None]]] = None

        # websocketのURL
        if secure_connect:
            self.__WS_URL = f"wss://{instance}/streaming"
        else:
            self.__WS_URL = f"ws://{instance}/streaming"
        if token is not None:
            self.__WS_URL += f"?i={token}"

        # logger作成
        self.__logger = logging.getLogger("Bromine")
        # logを簡単にできるよう部分適用する
        self.__log = partial(self.__logger.log, logging.DEBUG)

        # 再接続する奴を設定
        self.add_comeback(self.__ws_comeback_reconnect, block=True)

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

    @property
    def expect_info_func(self) -> Union[Callable[[dict[str, Any]], Coroutine[Any, Any, None]], None]:
        """謎の場所からくる情報を受け取る非同期関数

        普通は特に設定しなくてもよい"""
        return self.__expect_info_func

    @expect_info_func.setter
    def expect_info_func(self, func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(ExceptionTexts.FUNCTION_NOT_COROUTINEFUNC)
        self.__expect_info_func = func

    @expect_info_func.deleter
    def expect_info_func(self) -> None:
        self.__expect_info_func = None

    async def main(self) -> NoReturn:
        """処理を開始する関数"""
        self.__log("start main.")

        self.__is_running = True
        # send_queueをinitで作るとattached to a different loopとかいうゴミでるのでここで宣言
        self.__send_queue = asyncio.Queue()
        # バックグラウンドタスクの集合
        backgrounds = BackgroundTasks()

        try:
            await asyncio.create_task(self.__runner(backgrounds))
        finally:
            backgrounds.tasks_cancel()
            self.__is_running = False
            self.__log("finish main.")

    async def __runner(self, background_tasks: BackgroundTasks) -> NoReturn:
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

                    # 送るdaemonの作成
                    wsd = asyncio.create_task(self.__ws_send_d(ws))

                    # 接続に成功したということでfail_countを0に
                    connect_fail_count = 0
                    while True:
                        # データ受け取り
                        data = json.loads(await ws.recv())
                        if (type_ := data["type"]) in self.__ws_type_id_dict:
                            if (id := data["body"].get("id")) and id in self.__ws_type_id_dict[type_]:
                                background_tasks.add(asyncio.create_task(self.__ws_type_id_dict[type_][id](data["body"])))
                            elif (wild_func := self.__ws_type_id_dict[type_].get("ALLMATCH")):
                                # ワイルドカードがある時
                                background_tasks.add(asyncio.create_task(wild_func(data["body"])))
                            else:
                                # type情報には載ってるけどidが一致しない...どういう状況だ？
                                # expect_info_funcに流しておく
                                if self.__expect_info_func is not None:
                                    background_tasks.add(asyncio.create_task(self.__expect_info_func(data)))
                        else:
                            # 謎の場所からきた物
                            if self.__expect_info_func is not None:
                                background_tasks.add(asyncio.create_task(self.__expect_info_func(data)))

            except asyncio.exceptions.TimeoutError as e:
                # 接続がタイムアウトしたとき
                self.__log(f"error occured: Timeout {e}")
                self.__runner_exception_wait(connect_fail_count)

            except websockets.ConnectionClosed as e:
                # websocketが勝手に切れたりしたとき
                self.__log(f"error occured: Websocket Error [{e}]")
                self.__runner_exception_wait(connect_fail_count)

            except websockets.exceptions.InvalidStatusCode as e:
                # ステータスコードが変な時
                self.__log(f"error occured: Invalid Status Code [{e.status_code}]")
                if e.status_code // 100 == 4:
                    # 400番台
                    raise e
                else:
                    await self.__runner_exception_wait(connect_fail_count)

            except Exception as e:
                # 予定外のエラー発生時。
                self.__log(f"fatal Error: {type(e)}, args: {e.args}")
                raise e

            finally:
                connect_fail_count += 1  # ここが処理されるのは何か例外が起きたときなので
                # 再接続する際、いろいろ初期化する
                if isinstance(wsd, asyncio.Task):
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

    async def __runner_exception_wait(self, fail_count: int) -> None:
        await asyncio.sleep(self.__COOL_TIME)
        if fail_count > 5:
            # Todo: 例外投げるべき？
            #       死にすぎてる～っていう例外を投げるようにする設定を追加するべき？
            #       現状30秒寝る
            await asyncio.sleep(30)

    def add_comeback(self,
                     func: Callable[[], Coroutine[Any, Any, None]],
                     block: bool = False,
                     id: Optional[str] = None) -> str:
        """comebackを作る関数

        Parameters
        ----------
        func: CoroutineFunction
            comeback時に実行する非同期関数
        block: bool, default False
            websocketとの交信をブロッキングして実行するか
        id: :obj:`str`, optional
            識別id、ない場合自動生成される

        Returns
        -------
        str
            識別id

        Raises
        ------
        TypeError
            非同期関数funcがcoroutinefunctionでない時
        ValueError
            idがすでに予約済みの場合

        Note
        ----
        返り値の識別idはdel_comebackで使用します

        また、idの指定がない場合、uuid4で自動生成されます"""
        if id is None:
            # もしIDがない時生成する
            id = uuid.uuid4()
        else:
            if id in self.__on_comebacks:
                raise ValueError(ExceptionTexts.ID_ALREADY_RESERVED)
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(ExceptionTexts.FUNCTION_NOT_COROUTINEFUNC)

        self.__on_comebacks[id] = (block, func)

        self.__log(f"addition comeback. id: {id}")

        return id

    def del_comeback(self, id: str) -> None:
        """comeback消すやつ

        Parameters
        ----------
        id: str
            識別id

        Raises
        ------
        ValueError
            識別idが不適のとき"""
        if id not in self.__on_comebacks:
            raise ValueError(ExceptionTexts.ID_INVALID)
        self.__on_comebacks.pop(id)
        self.__log(f"delete comeback. id: {id}")

    async def __ws_send_d(self, ws: websockets.WebSocketClientProtocol) -> NoReturn:
        """websocketの情報を送るdaemon"""
        while True:
            type_, body_ = await self.__send_queue.get()
            await ws.send(json.dumps({
                "type": type_,
                "body": body_
            }))

    async def __ws_comeback_reconnect(self) -> None:
        """comebackしたときに再接続するやつ"""
        for i, body in self.__ws_on_comebacks.items():
            self._ws_send(i[0], body)

    def _add_ws_reconnect(self, type: str, id: str, body: dict[str, Any]) -> None:
        """接続しなおした時に再接続(情報を送る)する物を追加する

        これは低レベルAPIなので普通は触らなくても大丈夫です。

        Parameters
        ----------
        type: str
            type情報
        id: str
            識別id
        body: dict[str, Any]
            body情報

        Raises
        ------
        ValueError
            type情報と識別idの組み合わせがすでに予約済みのとき。

        Note
        ----
        body["id"]は識別idに上書きされます。"""
        body["id"] = id

        if self.__ws_on_comebacks.get((type, id)):
            raise ValueError(ExceptionTexts.TYPE_AND_ID_ALREADY_RESERVED)

        self.__ws_on_comebacks[(type, id)] = body

    def _del_ws_reconnect(self, type: str, id: str) -> None:
        """接続しなおした時に再接続(情報を送る)する物を削除する

        これは低レベルAPIなので普通は触らなくても大丈夫です。

        Parameters
        ----------
        type: str
            type情報
        id: str
            識別id

        Raises
        ------
        ValueError
            type情報か識別idが不適のとき"""
        if self.__ws_on_comebacks.get((type, id)):
            self.__ws_on_comebacks.pop((type, id))
        else:
            raise ValueError(ExceptionTexts.TYPE_AND_ID_INVALID)

    def _add_ws_type_id(self, type: str, id: str, func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        """websocketの情報を振り分ける辞書に追加する

        これは低レベルAPIなので普通は触らなくても大丈夫です。

        Parameters
        ----------
        type: str
            type情報
        id: str
            識別id
        func: CoroutineFunction
            反応があった時に実行される非同期関数

        Raises
        -------
        TypeError
            非同期関数funcがcoroutinefunctionでない時
        ValueError
            idがすでに予約済みの場合

        Note
        ----
        idが`ALLMATCH`の場合、ワイルドカード(type情報に一致する、他の識別idに引っかからなかった情報)になります。

        ワイルドカードは、id情報が存在しない場合にも振り分けられます。(emojiAdded等)"""
        if not asyncio.iscoroutinefunction(func):
            # 関数が非同期関数じゃない時
            raise TypeError(ExceptionTexts.FUNCTION_NOT_COROUTINEFUNC)

        if self.__ws_type_id_dict.get(type):
            if id in self.__ws_type_id_dict[type]:
                # IDがもうすでに使われているとき
                raise ValueError(ExceptionTexts.ID_ALREADY_RESERVED)
        else:
            # 辞書にtypeが登録されてなかったら初期化
            self.__ws_type_id_dict[type] = {}

        self.__ws_type_id_dict[type][id] = func

    def _del_ws_type_id(self, type: str, id: str) -> None:
        """websocketの情報を振り分ける辞書から削除する

        これは低レベルAPIなので普通は触らなくても大丈夫です。

        Parameters
        ----------
        type: str
            type情報
        id: str
            識別id

        Raises
        ------
        ValueError
            type情報か識別idが不適のとき"""
        if type not in self.__ws_type_id_dict:
            raise ValueError(ExceptionTexts.TYPE_INVALID)
        if id not in self.__ws_type_id_dict[type]:
            raise ValueError(ExceptionTexts.ID_INVALID)

        self.__ws_type_id_dict[type].pop(id)

    def _ws_send(self, type: str, body: dict[str, Any]) -> None:
        """ウェブソケットへ情報を送る関数

        これは低レベルAPIなので普通は触らなくても大丈夫です。

        Parameters
        ----------
        type: str
            type情報
        body: dict[str, Any]
            body情報

        Raises
        ------
        RuntimeError
            メイン関数が実行されていない時に使った場合"""
        if self.__is_running:
            self.__send_queue.put_nowait((type, body))
        else:
            raise RuntimeError(ExceptionTexts.MAIN_FUNC_NOT_RUNNING)

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
        TypeError
            非同期関数funcがcoroutinefunctionでない時
        ValueError
            idがすでに予約済みの場合

        Note
        ----
        返り値の識別idはws_disconnectで使用します

        また、idの指定がない場合、uuid4で自動生成されます"""
        if id is None:
            # idがなかったら自動生成
            id = str(uuid.uuid4())

        body = {
            "channel": channel,
            "id": id,
            "params": params
        }
        self._add_ws_type_id("channel", id, func)
        self._add_ws_reconnect("connect", id, body)

        if self.__is_running:
            # もしsend_queueがある時(実行中の時)
            self._ws_send("connect", body)
            self.__log(f"connect channel. name: {channel}, id: {id}")
        else:
            # ない時(実行前)
            self.__log(f"connect channel before run. name: {channel}, id: {id}")

        return id

    def ws_disconnect(self, id: str) -> None:
        """チャンネルを接続解除する関数

        Parameters
        ----------
        id: str
            識別id

        Raises
        ------
        ValueError
            識別idが不適のとき"""
        self._del_ws_type_id("channel", id)
        self._del_ws_reconnect("connect", id)

        if self.__is_running:
            body = {"id": id}
            self._ws_send("disconnect", body)

        self.__log(f"disconnect channel. id: {id}")

    def ws_subnote(self, noteid: str, func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        """投稿をキャプチャする関数

        Parameters
        ----------
        noteid: str
            キャプチャするノートID
        func: CoroutineFunction

        Raises
        ------
        TypeError
            非同期関数funcがcoroutinefunctionでない時
        ValueError
            もうすでにキャプチャしている時"""
        body = {"id": noteid}
        self._add_ws_type_id("noteUpdated", noteid, func)
        self._add_ws_reconnect("subNote", noteid, body)

        if self.__is_running:
            self._ws_send("subNote", body)

        self.__log(f"subscribe note. id: {noteid}")

    def ws_unsubnote(self, noteid: str) -> None:
        """ノートのキャプチャを解除する関数

        Parameters
        ----------
        noteid: str
            キャプチャのを解除するノートID

        Raises
        ------
        ValueError
            ノートIDがまだキャプチャされていないものの時"""
        self._del_ws_type_id("noteUpdated", noteid)
        self._del_ws_reconnect("subNote", noteid)

        if self.__is_running:
            body = {"id": noteid}
            self._ws_send("unsubNote", body)

        self.__log(f"unsubscribe note. id: {noteid}")

    def ws_connect_deco(self, channel: str):
        """ws_connectのデコレーター版

        Parameters
        ----------
        channel: str
            チャンネル名"""
        if not isinstance(channel, str):
            raise TypeError(ExceptionTexts.DECO_ARG_INVALID)

        def _wrap(func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]):
            self.ws_connect(channel=channel, func=func)
            return func

        return _wrap

    def ws_subnote_deco(self, noteid: str):
        """ws_subnoteのデコレーター版

        Parameters
        ----------
        noteid: str
            ノートのid"""
        if not isinstance(noteid, str):
            raise TypeError(ExceptionTexts.DECO_ARG_INVALID)

        def _wrap(func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]):
            self.ws_subnote(noteid=noteid, func=func)
            return func

        return _wrap

    def add_comeback_deco(self, block: bool = False):
        """add_comebackのデコレーター版

        Parameters
        ----------
        block: :obj:`bool`, default False
            websocketとの交信をブロッキングして実行するか"""
        if not isinstance(block, bool):
            raise TypeError(ExceptionTexts.DECO_ARG_INVALID)

        def _wrap(func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]):
            self.add_comeback(func=func, block=block)
            return func

        return _wrap

    # deprecated funtions

    @deprecated("Use `_ws_send`")
    def ws_send(self, type: str, body: dict[str, Any]) -> None:
        return self._ws_send(type=type, body=body)

    @deprecated("Use `_del_ws_type_id`")
    def del_ws_type_id(self, type: str, id: str) -> None:
        return self._del_ws_type_id(type=type, id=id)

    @deprecated("Use `_add_ws_type_id`")
    def add_ws_type_id(self, type: str, id: str, func: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        return self._add_ws_type_id(type=type, id=id, func=func)

    @deprecated("Use `_del_ws_reconnect`")
    def del_ws_reconnect(self, type: str, id: str) -> None:
        return self._del_ws_reconnect(type=type, id=id)

    @deprecated("Use `_add_ws_reconnect`")
    def add_ws_reconnect(self, type: str, id: str, body: dict[str, Any]) -> None:
        return self._add_ws_reconnect(type=type, id=id, body=body)
