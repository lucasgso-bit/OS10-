"""Worker entry point — run this on every machine.

The worker registers itself automatically using the machine's hostname,
then claims and executes tasks from U_ROBOT_LOG in a loop.

Usage:
    python worker.py
"""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/worker.log", encoding="utf-8"),
    ],
)

from engine.worker_agent import WorkerAgent  # noqa: E402 — logging configured first


def main() -> None:
    WorkerAgent().start()


if __name__ == "__main__":
    main()
