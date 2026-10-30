from delta_bot.config import BotConfig


def test_choose_loadout_by_threshold():
    config = BotConfig({
        "maps": {"MAP": {"thresholds": [
            {"max": 10, "loadout": "low"},
            {"min": 11, "loadout": "high"},
        ]}},
        "loadouts": {"low": {}, "high": {}},
    })
    assert config.choose_loadout("MAP", 10) == "low"
    assert config.choose_loadout("MAP", 11) == "high"
