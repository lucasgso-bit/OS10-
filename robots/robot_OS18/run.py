"""Robot OS18 — Unificação de Títulos a Pagar.

Wraps the existing automation in src/. The worker calls Robot(task).run()
and this delegates to the workflow function.
"""

from __future__ import annotations

from robots.base import BaseRobot
from robots.robot_OS18.src.workflow import run


class Robot(BaseRobot):
    robot_id = 13

    def run(self) -> None:
        run()
