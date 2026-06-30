import time

import pygetwindow as gw


VALORES_PENDENTES_TITLE = "Descontar os Valores Pendentes"


def validar_tela_valores_pendentes(pedido: dict, timeout: int = 3) -> None:
    """Raise RuntimeError if the 'Descontar os Valores Pendentes' screen appears."""
    inicio = time.time()

    while time.time() - inicio < timeout:
        janelas = [j for j in gw.getAllTitles() if VALORES_PENDENTES_TITLE in j]

        if janelas:
            raise RuntimeError(
                f"Tela 'Descontar os Valores Pendentes' detectada para pedido {pedido.get('numerocm')}."
            )

        time.sleep(0.3)
