# Delta PC Screen Automation

PC-only automation framework based on visible screen capture and keyboard/mouse input. It does not include process memory access, DLL injection, Frida hooks, or packet manipulation.

## Objective

Detect the selected map and entry threshold, choose a configured loadout, equip it through the visible UI, start the match, then locate and drop configured items.

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
└─ pyproject.toml
```

## Initial setup

Use a fixed first-pass environment: Windows 10/11, 1920x1080, Windows display scale 100%, borderless window mode.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m delta_bot.main --dry-run
```

`--dry-run` captures and logs detected states without sending input. Set `window_title` in `config/loadouts.yaml` after confirming the exact game window title.

## Implementation plan

1. Capture and crop the game window using `dxcam`; fall back to `mss`.
2. Add screenshots/templates for lobby, map selection, loadout, loading, HUD, and backpack states.
3. Connect OCR for map names and threshold values.
4. Populate `config/loadouts.yaml` with real item labels and threshold rules.
5. Enable visible UI input only after state detection and verification work in dry-run mode.
6. Add per-state screenshots, timeout/retry handling, and a global emergency stop key.

The first milestone is map/threshold detection. Game-specific coordinates and templates remain configuration data rather than hard-coded code.
