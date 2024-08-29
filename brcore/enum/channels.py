from enum import Enum
from typing import TypedDict, Literal


class ChannelNames(Enum):
    HOME_TIMELINE = "homeTimeline"
    LOCAL_TIMELINE = "localTimeline"
    HYBRID_TIMELINE = "hybridTimeline"
    GLOBAL_TIMELINE = "globalTimeline"

    MAIN = "main"


class TimeLineEventNote(TypedDict):
    id: str
    type: Literal["note"]
