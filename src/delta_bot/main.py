from __future__ import annotations

import argparse
import logging

from .config import load_config
from .input_control import InputController
from .workflow import Workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="PC screen automation skeleton")
    parser.add_argument("--config", default="config/loadouts.yaml")
    parser.add_argument("--map", default="TARGET_MAP")
    parser.add_argument("--threshold", type=int, default=10000)
    parser.add_argument("--live", action="store_true", help="enable visible input")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    controller = InputController(dry_run=not args.live)
    Workflow(config, controller).run_once(args.map, args.threshold)


if __name__ == "__main__":
    main()
