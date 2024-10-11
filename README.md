# BromineCore
[ぶろみね](https://github.com/35enidoi/bromine35bot)くんのコア部分の実装、そしてmisskeyのwebsocketAPI単体の実装です。  

ローカルのノートを講読したり、通知を取得したり。リバーシも頑張れば実装できます。  

何か問題が発生したり追加してほしい機能があったらissueに書いてください  
頑張って実装したり解決します
# Example
簡単なタイムライン閲覧クライアントです。  
トークン無しでタイムラインをリアルタイムで閲覧できます。
```py
import asyncio
from brcore import Bromine, enum


INSTANCE = "misskey.io"
TL = enum.MisskeyChannelNames.LOCAL_TIMELINE


def note_printer(note: dict) -> None:
    """ノートの情報を受け取って表示する関数"""
    NOBASIBOU_LENGTH = 20
    user = note["user"]
    username = user["name"] if user["name"] is not None else user["username"]
    print("-"*NOBASIBOU_LENGTH)
    if note.get("renoteId") and note["text"] is None:
        # リノートのときはリノート先だけ書く
        print(f"{username}がリノート")
        note_printer(note["renote"])
        # リノートはリアクション数とか書きたくないので
        # ここで返す
        print("-"*NOBASIBOU_LENGTH)
        return
    else:
        # 普通のノート
        print(f"{username}がノート ノートid: {note['id']}")
    if note.get("reply"):
        # リプライがある場合
        print("リプライ:")
        note_printer(note["reply"])
    if note.get("text"):
        print("テキスト:")
        print(note["text"])
    if note.get("renoteId"):
        # 引用
        print("引用:")
        note_printer(note["renote"])
    if len(note["files"]) != 0:
        # ファイルがある時
        print(f"ファイル数: {len(note['files'])}")
    # リアクションとかを書く
    print(f"リプライ数: {note['repliesCount']}, リノート数: {note['renoteCount']}, リアクション数: {note['reactionCount']}")
    reactions = []
    for reactionid, val in note["reactions"].items():
        if reactionid[-3:] == "@.:":
            # ローカルのカスタム絵文字のidはへんなのついてるので
            # それを消す
            reactionid = reactionid[:-3] + ":"
        reactions.append(f"({reactionid}, {val})")
    if len(reactions) != 0:
        print("リアクション達: ", ", ".join(reactions))
    print("-"*NOBASIBOU_LENGTH)


async def note_async(note: dict) -> None:
    """上のprinterの引数を調整するやつ

    asyncにするのはws_connectでは非同期関数が求められるので(見た目非同期っていう体にしているだけ)"""
    note_printer(note["body"])
    print()  # 空白をノート後に入れておく


async def main() -> None:
    brm = Bromine(instance=INSTANCE)
    brm.ws_connect(TL, note_async)
    print("start...")
    await brm.main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("fin")

```