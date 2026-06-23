"""Robot OS20 — Ticket Log Nota Import.

Wraps the existing automation in src/. The worker calls Robot(task).run()
and this delegates to the single-cycle workflow function.

Developed by: MATHEUS CORREA
Updated by: MATHEUS CORREA
Last Modified: 2026-06-15
Version: 1.0.0
"""

from __future__ import annotations

from robots.base import BaseRobot
from robots.robot_OS02.src.workflow import run_once


class Robot(BaseRobot):
    robot_id = 15

    def run(self) -> None:
        run_once(log_id=self.log_id)
