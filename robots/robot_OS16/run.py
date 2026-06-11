"""Robot OS16 — WNota OS16.

Wraps the existing automation in src/. The worker calls Robot(task).run()
and this delegates to the single-cycle workflow function.
"""

from __future__ import annotations

from robots.base import BaseRobot
from robots.robot_OS16.src.workflow import run_once


class Robot(BaseRobot):
    robot_id = 9

    def run(self) -> None:
        run_once(log_id=self.log_id)
