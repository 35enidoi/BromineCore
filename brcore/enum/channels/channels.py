from typing import NamedTuple

from brcore.enum.channels.channel_argtype import (
    EmptyArgsType, ChannelArgsType, AntennaArgsType, UserListArgsType, RoleTimelineArgsType,
    ReversiGameArgsType, HashtagArgsType
)


class MisskeyChannelNames(NamedTuple):
    # Timelines like
    HOME_TIMELINE = "homeTimeline"
    LOCAL_TIMELINE = "localTimeline"
    HYBRID_TIMELINE = "hybridTimeline"
    GLOBAL_TIMELINE = "globalTimeline"

    CHANNEL = "channel"
    ANTENNA = "antenna"
    USER_LIST = "userList"
    ROLE_TIMELINE = "roleTimeline"

    # User information
    MAIN = "main"
    DRIVE = "drive"

    # Other
    REVERSI = "reversi"
    REVERSI_GAME = "reversiGame"

    HASHTAG = "hashtag"

    ADMIN = "admin"

    SERVER_STATS = "serverStats"
    QUEUE_STATS = "queueStats"


class MisskeyChannelArgs:
    @staticmethod
    def HomeTimeline() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def LocalTimeline() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def HybridTimeline() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def GlobalTimeline() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def Channel(channelId: str) -> ChannelArgsType:
        return ChannelArgsType(channelId=channelId)

    @staticmethod
    def Antenna(antennaId: str) -> AntennaArgsType:
        return AntennaArgsType(antennaId=antennaId)

    @staticmethod
    def UserList(listId: str, withFiles: bool = False, withRenotes: bool = True) -> UserListArgsType:
        return UserListArgsType(listId=listId, withFiles=withFiles, withRenotes=withRenotes)

    @staticmethod
    def RoleTimeline(roleId: str) -> RoleTimelineArgsType:
        return RoleTimelineArgsType(roleId=roleId)

    @staticmethod
    def Main() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def Drive() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def Reversi() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def ReversiGame(gameId: str) -> ReversiGameArgsType:
        return ReversiGameArgsType(gameId=gameId)

    @staticmethod
    def Hashtag(q: list[list[str]]) -> HashtagArgsType:
        """
        q
          List of hashtags, e.g. `[['#hashtag1', '#hashtag2'], ['#hashtag3']]`
        """
        return HashtagArgsType(q=q)

    @staticmethod
    def Admin() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def ServerStats() -> EmptyArgsType:
        return EmptyArgsType()

    @staticmethod
    def QueueStats() -> EmptyArgsType:
        return EmptyArgsType()
