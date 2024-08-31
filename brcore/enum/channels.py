from __future__ import annotations

from enum import Enum


class ChannelNames(Enum):
    HOME_TIMELINE = "homeTimeline"
    LOCAL_TIMELINE = "localTimeline"
    HYBRID_TIMELINE = "hybridTimeline"
    GLOBAL_TIMELINE = "globalTimeline"

    MAIN = "main"
