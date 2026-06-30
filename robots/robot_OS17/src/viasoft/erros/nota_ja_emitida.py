import time

import pygetwindow as gw


NOTA_JA_EMITIDA_TITLE = "Atenção"
NOTA_JA_EMITIDA_MSG = "já emitida"


def validar_nota_ja_emitida(timeout: int = 3) -> None:
    """Raise RuntimeError if the 'Nota já emitida' attention popup appears."""
    inicio = time.time()

    while time.time() - inicio < timeout:
        janelas = [j for j in gw.getAllTitles() if NOTA_JA_EMITIDA_TITLE in j]

        if janelas:
            raise RuntimeError("Nota fiscal já emitida para este pedido.")

        time.sleep(0.3)
