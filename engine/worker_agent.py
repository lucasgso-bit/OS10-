"""Worker agent — runs on every machine.

On startup it registers itself in U_ROBOT_WORKER using COMPUTADOR_ROBO
(from config/.env). It then loops:

  1. Send heartbeat to U_ROBOT_WORKER
  2. Try to claim one PENDENTE task via SELECT FOR UPDATE SKIP LOCKED
  3. If a task was claimed, load the matching robot module and call run()
  4. Mark the task SUCESSO or ERRO
  5. If no task was found, sleep and retry

Because the claim is atomic at the database level, four machines can call
this simultaneously and each will get a different task — no duplicates,
no coordination needed between machines.
"""

from __future__ import annotations

import ctypes
import importlib
import logging
import signal
import threading
import time

from config import COMPUTADOR_ROBO
from core.database import (
    buscar_executando,
    check_task_status,
    claim_task,
    complete_task,
    fail_task,
    get_connection,
    heartbeat,
    init_oracle_client,
    register_worker,
    set_worker_offline,
)
from robots import ROBOT_REGISTRY

logger = logging.getLogger(__name__)

_SLEEP_IDLE = 30       # seconds to wait when queue is empty
_SLEEP_ERROR = 10      # seconds to wait after an unexpected error
_HEARTBEAT_EVERY = 30  # seconds between heartbeat updates
_INTERRUPT_CHECK = 180 # seconds between interrupt checks (3 minutes)


class _RobotCancelledError(BaseException):
    """Injected into the robot thread when an interrupt is detected in U_ROBOT_LOG."""


def _inject_exception(thread_id: int, exc_type: type) -> bool:
    """Raise exc_type asynchronously inside the target thread. Returns True on success."""
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(thread_id),
        ctypes.py_object(exc_type),
    )
    return res == 1


class WorkerAgent:
    def __init__(self) -> None:
        self.name = COMPUTADOR_ROBO
        self._running = True
        self._last_heartbeat: float = 0.0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def start(self) -> None:
        init_oracle_client()

        with get_connection() as conn:
            register_worker(conn, self.name)

        logger.info("Worker '%s' online", self.name)

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        while self._running:
            try:
                self._cycle()
            except Exception:
                logger.exception("Unexpected error in worker cycle")
                time.sleep(_SLEEP_ERROR)

        self._go_offline()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _cycle(self) -> None:
        now = time.monotonic()

        with get_connection() as conn:
            if now - self._last_heartbeat >= _HEARTBEAT_EVERY:
                heartbeat(conn, self.name)
                self._last_heartbeat = now

            executando = buscar_executando(conn, self.name)
            if executando:
                logger.debug(
                    "Robot '%s' (id=%d) already EXECUTANDO on computer '%s' — skipping",
                    executando["nome"],
                    executando["u_robot_id"],
                    self.name,
                )
                time.sleep(_SLEEP_IDLE)
                return

            task = claim_task(conn, self.name)

        if not task:
            time.sleep(_SLEEP_IDLE)
            return

        # Keep claiming until we find a task with a registered module.
        while task and not ROBOT_REGISTRY.get(task["robot_id"]):
            logger.warning(
                "Nenhum módulo registrado para robot_id=%d (log_id=%d) — "
                "marcando ERRO e tentando próximo.",
                task["robot_id"],
                task["log_id"],
            )
            with get_connection() as conn:
                fail_task(conn, task["log_id"], f"Nenhum módulo registrado para robot_id={task['robot_id']}")
            with get_connection() as conn:
                task = claim_task(conn, self.name)

        if not task:
            time.sleep(_SLEEP_IDLE)
            return

        self._execute(task)

    def _execute(self, task: dict) -> None:
        robot_id: int = task["robot_id"]
        log_id: int = task["log_id"]

        logger.info("Starting robot_id=%d log_id=%d", robot_id, log_id)

        robot_exc: list[BaseException] = []
        done = threading.Event()

        def _run() -> None:
            try:
                module_path = ROBOT_REGISTRY.get(robot_id)
                if not module_path:
                    raise ValueError(f"Nenhum módulo registrado para robot_id={robot_id}")
                module = importlib.import_module(module_path)
                robot = module.Robot(task)
                robot.run()
            except _RobotCancelledError:
                pass
            except BaseException as exc:  # noqa: BLE001
                robot_exc.append(exc)
            finally:
                done.set()

        t = threading.Thread(target=_run, name=f"robot-{robot_id}-{log_id}", daemon=True)
        t.start()

        # Poll U_ROBOT_LOG every 3 minutes while the robot runs.
        # If the status is no longer EXECUTANDO, the robot was interrupted externally.
        while not done.wait(_INTERRUPT_CHECK):
            try:
                with get_connection() as conn:
                    status = check_task_status(conn, log_id)
            except Exception:
                logger.warning("Could not check interrupt status for log_id=%d", log_id)
                continue

            if status != "EXECUTANDO":
                logger.info(
                    "log_id=%d status changed to '%s' — interrupting robot_id=%d",
                    log_id, status, robot_id,
                )
                _inject_exception(t.ident, _RobotCancelledError)
                done.wait(15)  # give the robot up to 15 s to clean up
                logger.info("robot_id=%d log_id=%d interrupted", robot_id, log_id)
                return  # status was already updated externally — nothing else to do

        # Robot finished naturally; update status based on outcome.
        if robot_exc:
            exc = robot_exc[0]
            logger.exception("robot_id=%d log_id=%d FAILED", robot_id, log_id, exc_info=exc)
            with get_connection() as conn:
                fail_task(conn, log_id, str(exc))
        else:
            logger.info("robot_id=%d log_id=%d finished OK", robot_id, log_id)
            with get_connection() as conn:
                complete_task(conn, log_id)

    def _go_offline(self) -> None:
        try:
            with get_connection() as conn:
                set_worker_offline(conn, self.name)
        except Exception:
            logger.warning("Could not set worker offline in database")
        logger.info("Worker '%s' offline", self.name)

    def _handle_shutdown(self, *_) -> None:
        logger.info("Shutdown signal received")
        self._running = False
