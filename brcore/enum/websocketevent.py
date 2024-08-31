from typing import TypedDict, Literal

from brcore.enum.events import EventAnnouncementCreated, ChannelEvents


class WebsocketEventAnnouncementCreated(TypedDict):
    type: Literal["announcementCreated"]
    body: dict[Literal["announcement"], EventAnnouncementCreated]


class WebsocketEventChannel(TypedDict):
    type: Literal["channel"]
    body: ChannelEvents
