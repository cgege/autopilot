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

    def plan_from_detected_map(self, map_name: str, threshold: int) -> dict:
        """Build a plan after OCR/template detection; this path never selects a map."""
        if self.config.waits_for_teammate_map:
            self.states.transition(State.WAITING_FOR_TEAMMATE_MAP)
        self.states.transition(State.MAP_DETECTED)
        return self.dry_run_plan(map_name, threshold)

    def plan_from_detected_mode(self, mode: str, equipment_value: int,
                                map_name: str = "UNKNOWN_MAP") -> dict:
        """Build a plan from 机密/绝密; map_name is retained for logging only."""
        if self.config.waits_for_teammate_map:
            self.states.transition(State.WAITING_FOR_TEAMMATE_MAP)
        self.states.transition(State.MAP_DETECTED)
        loadout_name = self.config.choose_loadout_for_mode(mode, equipment_value)
        plan = {
            "map": map_name,
            "mode": mode,
            "equipment_value": equipment_value,
            "loadout_name": loadout_name,
            "loadout": self.config.loadout(loadout_name),
            "drop_items": self.config.raw.get("drop_items", []),
        }
        LOGGER.info("plan=%s", plan)
        return plan

    def run_once(self, map_name: str, threshold: int) -> None:
        plan = self.plan_from_detected_map(map_name, threshold)
        LOGGER.info("selected plan: %s", plan)
        # TODO: connect template detections and configured click points.
        self.states.transition(State.LOADOUT_READY)
        self.states.transition(State.LOADOUT_CONFIRMED)
        self.states.transition(State.MATCH_LOADING)
        self.states.transition(State.ENTRY_WARNING)
        self.states.transition(State.ENTRY_CONTINUED)
        self.states.transition(State.IN_MATCH)
        self.states.transition(State.BACKPACK_OPEN)
        self.states.transition(State.SKILL_ITEM_FOUND)
        self.states.transition(State.POST_DROP_ACTION)
        self.states.transition(State.DROP_VERIFIED)
