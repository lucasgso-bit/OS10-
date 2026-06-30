import time

import pyautogui
import pygetwindow as gw
from pywinauto import Desktop


VIASOFT_WINDOW_TITLE = "AGRO-AG"
NF_NUMBER_CLASS = "TVsNumRight"
NF_NUMBER_INDEX = 15
NF_SEQNOTA_INDEX = 16


def focar_janela_viasoft() -> None:
    janelas = [j for j in gw.getAllTitles() if j.startswith(VIASOFT_WINDOW_TITLE)]
    if janelas:
        gw.getWindowsWithTitle(janelas[0])[0].activate()
        time.sleep(0.5)


def aguardar_autorizacao_nfe(timeout: int = 120) -> None:
    """Wait for NFe authorization status 100."""
    inicio = time.time()

    while time.time() - inicio < timeout:
        janelas = [j for j in gw.getAllTitles() if "100" in j or "autoriza" in j.lower()]
        if janelas:
            return
        time.sleep(1)

    raise TimeoutError("NFe não autorizada dentro do tempo limite.")


def fechar_tela_impressao() -> None:
    """Close the print screen after NF authorization."""
    focar_janela_viasoft()
    time.sleep(0.5)
    pyautogui.press("escape")
    time.sleep(1)


def coletar_numero_nota() -> dict:
    """Collect nota and seqnota from the NF screen using pywinauto."""
    janelas_pw = Desktop(backend="win32").windows()
    janela_viasoft = None

    for j in janelas_pw:
        try:
            if j.window_text().startswith(VIASOFT_WINDOW_TITLE):
                janela_viasoft = j
                break
        except Exception:
            continue

    if janela_viasoft is None:
        raise RuntimeError("Janela Viasoft não encontrada para coletar número da nota.")

    controles = janela_viasoft.descendants(class_name=NF_NUMBER_CLASS)

    nota = controles[NF_NUMBER_INDEX].window_text().strip()
    seqnota = controles[NF_SEQNOTA_INDEX].window_text().strip()

    return {"nota": nota, "seqnota": seqnota}


def salvar_nf_final() -> None:
    """Save the NF after collecting the numbers."""
    focar_janela_viasoft()
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)


def finalizar_parte_2() -> dict:
    """Validate NFe authorization, close print, collect nota/seqnota, and save."""
    aguardar_autorizacao_nfe()
    fechar_tela_impressao()
    resultado = coletar_numero_nota()
    salvar_nf_final()
    return resultado
