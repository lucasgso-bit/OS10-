"""Start the orchestrator robot.

Claim the next PENDENTE task from U_ROBOT_LOG and execute the matching robot.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-08
Version: 3.0.0
"""

import importlib
import time

from core.database import claim_any_task, get_connection, init_oracle_client
from robots import ROBOT_REGISTRY

_SLEEP_IDLE = 30  # segundos de espera quando a fila está vazia


def main() -> None:
    """Loop 24/7: claim and run tasks forever, sleeping when the queue is empty."""
    init_oracle_client()

    while True:
        try:
            with get_connection() as conn:
                task = claim_any_task(conn, computer_name=_computer_name())

            if not task:
                print(f"Nenhuma tarefa PENDENTE na fila. Aguardando {_SLEEP_IDLE}s...")
                time.sleep(_SLEEP_IDLE)
                continue

            robot_id: int = task["robot_id"]
            module_path = ROBOT_REGISTRY.get(robot_id)

            if not module_path:
                print(f"Nenhum módulo registrado para robot_id={robot_id}.")
                time.sleep(_SLEEP_IDLE)
                continue

            module = importlib.import_module(module_path)
            module.Robot(task).run()

        except KeyboardInterrupt:
            print("Encerrando...")
            break
        except Exception as e:
            print(f"Erro no ciclo principal: {e}")
            time.sleep(_SLEEP_IDLE)


def _computer_name() -> str:
    from config import COMPUTADOR_ROBO
    return COMPUTADOR_ROBO


if __name__ == "__main__":
    main()
