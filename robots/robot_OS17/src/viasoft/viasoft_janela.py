import time

import pygetwindow as gw


def focar_janela_por_titulo(titulo: str, timeout: int = 30) -> None:
    """Focus a window whose title starts with the given string."""
    inicio = time.time()

    while time.time() - inicio < timeout:
        janelas = [j for j in gw.getAllTitles() if j.startswith(titulo)]

        if janelas:
            janela = gw.getWindowsWithTitle(janelas[0])[0]
            janela.activate()
            time.sleep(0.5)
            return

        time.sleep(0.5)

    raise TimeoutError(f"Janela '{titulo}' não encontrada em {timeout}s.")
