from typing import TypedDict, Literal, Union

from brcore.enum.misskeytypes import (
    Note,
    AnnouncementCreated,
    Notification
)


class EventTimeLineNote(TypedDict):
    id: str
    type: Literal["note"]
    body: list[Note]


class EventMainNotification(TypedDict):
    id: str
    type: Literal["notification"]
    body: Notification


class EventMainUnreadNotification(TypedDict):
    id: str
    type: Literal["unreadNotification"]
    body: Notification


class EventMainRenote(TypedDict):
    id: str
    type: Literal["renote"]
    body: Note


class EventMainReply(TypedDict):
    id: str
    type: Literal["reply"]
    body: Note


class EventMainMention(TypedDict):
    id: str
    type: Literal["mention"]
    body: Note


class EventMainUnreadMention(TypedDict):
    id: str
    type: Literal["unreadMention"]
    body: str


class EventAnnouncementCreated(TypedDict):
    announcement: AnnouncementCreated


MainEvents = Union[
    EventMainNotification, EventMainUnreadNotification, EventMainRenote,
    EventMainReply, EventMainMention, EventMainUnreadMention
]
ChannelEvents = Union[EventTimeLineNote, MainEvents]
