"""Robot 007 — WNota 255/275.

Wraps the existing automation in src/. The worker calls Robot(task).run()
and this delegates to the single-cycle workflow function.
"""

from __future__ import annotations

from robots.base import BaseRobot
from robots.robot_OS07.src.workflow import run_once


class Robot(BaseRobot):
    robot_id = 11

    def run(self) -> None:
        run_once()
