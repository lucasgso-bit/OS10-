from __future__ import annotations

from robots.base import BaseRobot
from robots.robot_OS10.src.workflow import run_once



class Robot(BaseRobot):
    robot_id = 10

    def run(self) -> None:
        task = getattr(self, "task", None) or {}

        run_once(
            log_id=self.log_id,
            task=task,
        )
