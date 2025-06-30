from typing import TypedDict, NotRequired


class MisskeyChannelArgsTypeBase(TypedDict):
    pass


class EmptyArgsType(MisskeyChannelArgsTypeBase):
    pass


class ChannelArgsType(MisskeyChannelArgsTypeBase):
    channelId: str


class AntennaArgsType(MisskeyChannelArgsTypeBase):
    antennaId: str


class UserListArgsType(MisskeyChannelArgsTypeBase):
    listId: str
    withFiles: NotRequired[bool]
    withRenotes: NotRequired[bool]


class RoleTimelineArgsType(MisskeyChannelArgsTypeBase):
    roleId: str


class ReversiGameArgsType(MisskeyChannelArgsTypeBase):
    gameId: str


class HashtagArgsType(MisskeyChannelArgsTypeBase):
    q: list[list[str]]  # List of hashtags
