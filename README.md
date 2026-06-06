# BromineCore
MisskeyのWebsocketAPI単体の実装です。  

ノートを講読したり、通知を取得したり。リバーシbotも頑張れば実装できます。  

# Example
簡単なタイムライン閲覧クライアントです。  
トークン無しでタイムラインをリアルタイムで閲覧できます。
```py
import asyncio
from brcore import Bromine, enum


INSTANCE = "misskey.io"
TL = enum.MisskeyChannelNames.LOCAL_TIMELINE
TL_ARGS = enum.MisskeyChannelArgs.LocalTimeline()

brm = Bromine(instance=INSTANCE)


def note_printer(note: dict) -> None:
    """ノートの情報を受け取って描画する関数"""
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
        print(f"{username}が投稿しました。 noteid: {note['id']}")

    if note.get("reply"):
        # リプライがある場合
        print("リプライ:")
        note_printer(note["reply"])
    if note.get("text"):
        # 本文
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
            # ローカルのカスタム絵文字のidはへんなのついてるので消す
            reactionid = reactionid[:-3] + ":"
        reactions.append(f"({reactionid}, {val})")
    if len(reactions) != 0:
        print("リアクション: ", ", ".join(reactions))

    print("-"*NOBASIBOU_LENGTH)


@brm.ws_connect_deco(TL, **TL_ARGS)
async def note_async(note: dict) -> None:
    note_printer(note["body"])
    print()  # 空白をノート後に入れておく


# デコレータを使わない場合は、下のように書くこともできる
# brm.ws_connect(TL, note_async, **TL_ARGS)


if __name__ == "__main__":
    try:
        print("start...")
        asyncio.run(brm.main())
    except KeyboardInterrupt:
        print("fin")

```