from __future__ import annotations

from enum import Enum, auto


class State(Enum):
    LOBBY = auto()
    WAITING_FOR_TEAMMATE_MAP = auto()
    MAP_DETECTED = auto()
    LOADOUT_READY = auto()
    MATCH_LOADING = auto()
    IN_MATCH = auto()
    BACKPACK_OPEN = auto()
    SKILL_ITEM_FOUND = auto()
    POST_DROP_ACTION = auto()
    DROP_VERIFIED = auto()
    LOADOUT_CONFIRMED = auto()
    ENTRY_WARNING = auto()
    ENTRY_CONTINUED = auto()
    FAILED = auto()


class StateMachine:
    def __init__(self) -> None:
        self.state = State.LOBBY

    def transition(self, state: State) -> None:
        self.state = state
