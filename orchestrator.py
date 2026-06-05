"""Orchestrator entry point — run this on one machine (the "master").

Reads U_ROBOT every 60 s and creates PENDENTE tasks in U_ROBOT_LOG
for robots that are due. Workers on all machines pick up those tasks
automatically.

Usage:
    python orchestrator.py
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/orchestrator.log", encoding="utf-8"),
    ],
)

from engine.scheduler import Orchestrator  # noqa: E402 — logging configured first


def main() -> None:
    Orchestrator().start()


if __name__ == "__main__":
    main()
