from enum import Enum


class State(Enum):
    IDLE = 0
    BUFFERING = 1
    READY = 2
    END = 3
