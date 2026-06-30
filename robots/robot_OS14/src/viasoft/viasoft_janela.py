import time

import pygetwindow as gw


def focar_janela_por_titulo(titulo: str, timeout: int = 30) -> None:
    for _ in range(timeout):
        janelas = gw.getWindowsWithTitle(titulo)

        if janelas:
            print(f"Focando na tela {titulo}")

            janela = janelas[-1]

            if janela.isMinimized:
                janela.restore()

            janela.activate()
            time.sleep(1)
            return

        time.sleep(1)

    raise RuntimeError(f"Janela não encontrada: {titulo}")
