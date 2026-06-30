import time

import pyautogui
import pygetwindow as gw


def tratar_tela_atencao(timeout: int = 3) -> bool:
    for _ in range(timeout):
        janelas = [
            janela
            for janela in gw.getAllWindows()
            if "atenção" in janela.title.lower()
        ]

        if janelas:
            janela = janelas[-1]

            try:
                if janela.isMinimized:
                    janela.restore()

                janela.activate()
                time.sleep(0.5)

            except Exception:
                pass

            pyautogui.press("enter")
            time.sleep(1)

            print("Tela de Atenção tratada.")
            return True

        time.sleep(1)

    return False
