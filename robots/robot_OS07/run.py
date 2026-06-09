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
        import time
        while True:
            try:
                run_once(log_id=self.log_id)
            except Exception as e:
                print(f"Erro no ciclo OS07: {e}")
            print("Aguardando 20 segundos antes do próximo ciclo...\n")
            time.sleep(20)
