from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ThresholdRule:
    loadout: str
    minimum: int | None = None
    maximum: int | None = None

    def matches(self, value: int) -> bool:
        return ((self.minimum is None or value >= self.minimum)
                and (self.maximum is None or value <= self.maximum))


@dataclass(frozen=True)
class BotConfig:
    raw: dict[str, Any]

    @property
    def window_title(self) -> str:
        return str(self.raw.get("window_title", ""))

    @property
    def dry_run(self) -> bool:
        return bool(self.raw.get("capture", {}).get("dry_run", True))

    @property
    def waits_for_teammate_map(self) -> bool:
        workflow = self.raw.get("workflow", {})
        return bool(workflow.get("wait_for_teammate_map", True))

    @property
    def verify_each_action(self) -> bool:
        return bool(self.raw.get("workflow", {}).get("verify_each_action", True))

    def choose_loadout_for_mode(self, mode: str, equipment_value: int) -> str:
        """Select by mode only; the map name is intentionally irrelevant."""
        mode_config = self.raw.get("modes", {}).get(mode)
        if not mode_config:
            raise KeyError(f"No mode rule configured for {mode!r}")
        minimum_value = int(mode_config["minimum_equipment_value"])
        if equipment_value < minimum_value:
            raise ValueError(
                f"Equipment value {equipment_value} is below {mode!r} minimum {minimum_value}"
            )
        return str(mode_config["loadout"])

    def choose_loadout(self, map_name: str, threshold: int) -> str:
        map_config = self.raw.get("maps", {}).get(map_name)
        if not map_config:
            raise KeyError(f"No map rule configured for {map_name!r}")
        direct_loadout = map_config.get("loadout")
        minimum_value = map_config.get("minimum_equipment_value")
        if direct_loadout is not None:
            if minimum_value is not None and threshold < int(minimum_value):
                raise ValueError(
                    f"Equipment value {threshold} is below {map_name!r} minimum {minimum_value}"
                )
            return str(direct_loadout)
        for item in map_config.get("thresholds", []):
            rule = ThresholdRule(
                loadout=str(item["loadout"]),
                minimum=item.get("min"),
                maximum=item.get("max"),
            )
            if rule.matches(threshold):
                return rule.loadout
        raise ValueError(f"No loadout rule matches {map_name!r} threshold {threshold}")

    def loadout(self, name: str) -> dict[str, Any]:
        try:
            return dict(self.raw["loadouts"][name])
        except KeyError as exc:
            raise KeyError(f"Unknown loadout {name!r}") from exc


def load_config(path: str | Path) -> BotConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return BotConfig(data)
