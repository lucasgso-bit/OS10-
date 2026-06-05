"""Base class that every robot must inherit from."""

from __future__ import annotations

import logging


class BaseRobot:
    """Inherit this and implement run(). The worker handles everything else."""

    robot_id: int = 0

    def __init__(self, task: dict) -> None:
        self.task = task
        self.log_id = task["log_id"]
        self.logger = logging.getLogger(f"robot_{self.robot_id:03d}")

    def run(self) -> None:
        raise NotImplementedError(f"Robot {self.robot_id} must implement run()")
