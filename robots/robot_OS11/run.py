"""Robot OS11 — Cobrança de Taxas de Serviço.

Wraps the existing automation in src/. The worker calls Robot(task).run()
and this delegates to the workflow function.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

from robots.base import BaseRobot
from robots.robot_OS11.src.workflow import run


class Robot(BaseRobot):
    robot_id = 4

    def run(self) -> None:
        run()
