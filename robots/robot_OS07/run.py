"""Robot 007 — WNota 255/275.

Wraps the existing automation in src/. The worker calls Robot(task).run()
and this delegates to the single-cycle workflow function.
"""

from __future__ import annotations

from robots.base import BaseRobot
from src.workflow import run_once


class Robot(BaseRobot):
    robot_id = 7

    def run(self) -> None:
        run_once()
