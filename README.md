# Delta PC Screen Automation

PC-only automation framework based on visible screen capture and keyboard/mouse input. It does not include process memory access, DLL injection, Frida hooks, or packet manipulation.

## Objective

Wait for the teammate to select a mode, detect `机密` or `绝密`, choose a configured loadout, equip it through the visible UI, start the match, then locate and drop the configured skill item and run the configured post-drop action. The map name is logged but does not affect the loadout decision.

## Project layout

```text
delta_pc_automation/
├─ config/loadouts.yaml
├─ src/delta_bot/
│  ├─ capture.py
│  ├─ config.py
│  ├─ input_control.py
│  ├─ vision.py
│  ├─ state_machine.py
│  ├─ workflow.py
│  └─ main.py
├─ tests/test_config.py
├─ requirements.txt
├─ build.ps1
└─ pyproject.toml
```

## Initial setup

Use a fixed first-pass environment: Windows 10/11, 2560x1440, Windows display scale 100%, borderless window mode.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m delta_bot.main --dry-run
```

The CLI remains available for plan-only checks; use `--live` when invoking it directly. The desktop EXE uses the visible-input flow described below. Set `window_title` in `config/loadouts.yaml` after confirming the exact game window title.

## Implementation plan

1. Capture and crop the game window using `dxcam`; fall back to `mss`.
2. Add screenshots/templates for lobby, teammate-selected map, loadout, loading, HUD, backpack, and skill-item states.
3. Connect OCR for map names and threshold values.
4. Populate `config/loadouts.yaml` with real item labels and threshold rules.
5. Keep visible UI input behind the combined Start/Stop control and verify each action before expanding the flow.
6. Add per-state screenshots, timeout/retry handling, and a global emergency stop key.

The first milestone is mode detection after the teammate completes map selection. The bot does not click or change the map selection. Game-specific coordinates and templates remain configuration data rather than hard-coded code.

Current entry requirements in the sample configuration:

| Detected mode | Minimum equipment value | Loadout |
|---|---:|---|
| 零号大坝-机密 | 190000 | confidential |
| 航天基地-绝密 | 600000 | classified |

The workflow should verify the prepared equipment value before pressing the start button.

The provided loadout screenshot confirms a clickable `背包 / 未装配` slot on the left side. The initial anchor is recorded in `config/loadouts.yaml` as an approximate rectangle for 2560x1440; live input should first verify the text/icon template inside that rectangle.

Backpack selection rules from the supplied screenshots:

| Mode | Backpack | Flow |
|---|---|---|
| 机密 | GT5野战背包 | Scroll the left list to the bottom, select the row, verify the name, click the current lower-right purchase/exchange control |
| 绝密 | 重型登山包 | Scroll the left list to the bottom, select the row, verify the name, click the current lower-right purchase/exchange control |

Backpack price is dynamic and is intentionally ignored. The purchase control is clicked only after the selected-item name matches the configured rule, then the resulting equipped slot is verified.

After purchase, the workflow expects the equipped loadout screen (`确认配装`) and then the entry warning dialog (`仍要继续`). Both controls have dedicated 2560x1440 anchor rectangles and must be visually confirmed before clicking.

## EXE product form

The desktop entry point is `src/delta_bot/app.py`. It provides a combined Start/Stop toggle, status, and log output while the worker runs in a background thread. Build a single-window executable with:

```powershell
.\build.ps1
```

The output is `dist\DeltaScreenBot.exe`. The current live flow uses the supplied 2560x1440 screenshots and configured anchors to drive the lobby -> 配装 -> 背包 -> 购买/兑换 -> 确认配装 -> 仍要继续 sequence. The backpack list is scrolled in repeated rounds; GT5野战背包 clicks the price/purchase panel above `兑换`, while 重型登山包 uses its separate purchase panel. Keep the game at 2560x1440 and 100% Windows scaling, then click `自动识别开始` or choose `机密`/`绝密`. The single `开始`/`停止` button requests a cooperative stop.
