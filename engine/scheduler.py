"""Orchestrator — runs on one machine (or any machine, idempotently).

Reads U_ROBOT every minute and creates PENDENTE entries in U_ROBOT_LOG
when a robot is due to run. Workers pick those entries up automatically.

Scheduling rules (all must pass):
  - ATIVO = 'S'
  - No PENDENTE or EXECUTANDO task already exists for this robot
  - EXECMAXDIA not exceeded today (0 = unlimited)
  - Day of week is in DIAS (ignored when EXECTODOSDIAS = 'S')
  - INTERVALOMINUTOS elapsed since last successful run (0 = run immediately)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from core.database import (
    count_executions_today,
    create_pending_task,
    get_connection,
    get_last_success,
    get_scheduled_robots,
    has_active_task,
    init_oracle_client,
)

logger = logging.getLogger(__name__)

_CYCLE_INTERVAL = 60  # seconds between scheduler sweeps

_WEEKDAY_MAP = {
    0: "SEG",
    1: "TER",
    2: "QUA",
    3: "QUI",
    4: "SEX",
    5: "SAB",
    6: "DOM",
}


class Orchestrator:
    def start(self) -> None:
        init_oracle_client()
        logger.info("Orchestrator started")

        while True:
            try:
                self._cycle()
            except Exception:
                logger.exception("Orchestrator cycle error")
            time.sleep(_CYCLE_INTERVAL)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _cycle(self) -> None:
        with get_connection() as conn:
            robots = get_scheduled_robots(conn)
            for robot in robots:
                try:
                    if self._should_schedule(robot, conn):
                        task_id = create_pending_task(conn, robot["U_ROBOT_ID"])
                        logger.info(
                            "Task created: robot='%s' (id=%d) log_id=%d",
                            robot["NOME"],
                            robot["U_ROBOT_ID"],
                            task_id,
                        )
                except Exception:
                    logger.exception("Error evaluating robot '%s'", robot.get("NOME"))

    def _should_schedule(self, robot: dict, conn) -> bool:
        robot_id: int = robot["U_ROBOT_ID"]

        if has_active_task(conn, robot_id):
            return False

        max_per_day: int = robot.get("EXECMAXDIA") or 0
        if max_per_day > 0 and count_executions_today(conn, robot_id) >= max_per_day:
            return False

        if robot.get("EXECTODOSDIAS") != "S":
            allowed_days = [d.strip() for d in (robot.get("DIAS") or "").split(",")]
            today = _WEEKDAY_MAP[datetime.now().weekday()]
            if today not in allowed_days:
                return False

        interval_min: int = robot.get("INTERVALOMINUTOS") or 0
        if interval_min > 0:
            last_run = get_last_success(conn, robot_id)
            if last_run is not None:
                elapsed = (datetime.now() - last_run.replace(tzinfo=None)).total_seconds() / 60
                if elapsed < interval_min:
                    return False

        return True
