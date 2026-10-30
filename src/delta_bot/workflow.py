from __future__ import annotations

import logging

from .config import BotConfig
from .input_control import InputController
from .state_machine import State, StateMachine

LOGGER = logging.getLogger(__name__)


class Workflow:
    """High-level workflow; game-specific coordinates are intentionally externalized."""

    def __init__(self, config: BotConfig, controller: InputController):
        self.config = config
        self.controller = controller
        self.states = StateMachine()

    def dry_run_plan(self, map_name: str, threshold: int) -> dict:
        loadout_name = self.config.choose_loadout(map_name, threshold)
        plan = {
            "map": map_name,
            "threshold": threshold,
            "loadout_name": loadout_name,
            "loadout": self.config.loadout(loadout_name),
            "drop_items": self.config.raw.get("drop_items", []),
        }
        LOGGER.info("plan=%s", plan)
        return plan

    def run_once(self, map_name: str, threshold: int) -> None:
        plan = self.dry_run_plan(map_name, threshold)
        LOGGER.info("selected plan: %s", plan)
        self.states.transition(State.MAP_SELECTED)
        # TODO: connect template detections and configured click points.
        self.states.transition(State.LOADOUT_READY)
        self.states.transition(State.MATCH_LOADING)
        self.states.transition(State.IN_MATCH)
        self.states.transition(State.BACKPACK_OPEN)
        self.states.transition(State.DROP_VERIFIED)
