from __future__ import annotations

from enum import Enum, auto


class State(Enum):
    LOBBY = auto()
    MAP_SELECTED = auto()
    LOADOUT_READY = auto()
    MATCH_LOADING = auto()
    IN_MATCH = auto()
    BACKPACK_OPEN = auto()
    DROP_VERIFIED = auto()
    FAILED = auto()


class StateMachine:
    def __init__(self) -> None:
        self.state = State.LOBBY

    def transition(self, state: State) -> None:
        self.state = state
