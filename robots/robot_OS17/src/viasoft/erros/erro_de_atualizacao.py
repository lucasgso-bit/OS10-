import time

import pyautogui
import pygetwindow as gw


ERRO_ATUALIZACAO_TITLE = "Erro de Atualização"


def validar_tela_erro_de_atualizacao(pedido: dict, timeout: int = 3) -> None:
    """Raise RuntimeError if the 'Erro de Atualização' screen appears."""
    inicio = time.time()

    while time.time() - inicio < timeout:
        janelas = [j for j in gw.getAllTitles() if ERRO_ATUALIZACAO_TITLE in j]

        if janelas:
            screenshot_path = f"erro_atualizacao_{pedido.get('numerocm', 'unknown')}.png"
            pyautogui.screenshot(screenshot_path)
            raise RuntimeError(
                f"Tela 'Erro de Atualização' detectada para pedido {pedido.get('numerocm')}. "
                f"Screenshot: {screenshot_path}"
            )

        time.sleep(0.3)
