import time

import pyautogui
import pygetwindow as gw
from pywinauto import Desktop


TITULO_JANELA_NOTA = "Nota Fiscal"
CLASS_NAME_CAMPO_DATA = "TVsDateRight"
INSTANCE_CAMPO_DATA = 4
TIMEOUT_JANELA = 15
TIMEOUT_CAMPO = 10


def buscar_janela_nota_fiscal(timeout: int = TIMEOUT_JANELA):
    inicio = time.time()

    while time.time() - inicio < timeout:
        janelas = gw.getWindowsWithTitle(TITULO_JANELA_NOTA)

        if janelas:
            janela = janelas[-1]
            if janela.isMinimized:
                janela.restore()
                time.sleep(0.8)
            janela.activate()
            time.sleep(1)
            print(f"Janela Nota Fiscal encontrada: {janela.title}")
            return janela

        time.sleep(0.5)

    raise RuntimeError("Janela Nota Fiscal não encontrada após seleção de endereço.")


def obter_janela_pywinauto():
    janela_gw = buscar_janela_nota_fiscal()
    janela = Desktop(backend="win32").window(handle=janela_gw._hWnd)
    janela.wait("exists ready visible", timeout=TIMEOUT_JANELA)
    return janela


def obter_campo_data_emissao():
    janela = obter_janela_pywinauto()
    inicio = time.time()

    while time.time() - inicio < TIMEOUT_CAMPO:
        campos_data = janela.descendants(class_name=CLASS_NAME_CAMPO_DATA)

        if len(campos_data) >= INSTANCE_CAMPO_DATA:
            campo_data = campos_data[INSTANCE_CAMPO_DATA - 1]
            print(f"Campo de data encontrado: {CLASS_NAME_CAMPO_DATA}{INSTANCE_CAMPO_DATA}")
            return campo_data

        time.sleep(0.5)

    raise RuntimeError(
        f"Campo de data {CLASS_NAME_CAMPO_DATA}{INSTANCE_CAMPO_DATA} "
        "não encontrado após aguardar carregamento."
    )


def preencher_data_emissao(data_emissao: str) -> None:
    campo_data = obter_campo_data_emissao()

    print("Clicando no campo de data.")
    campo_data.click_input(coords=(35, 13))
    time.sleep(0.3)
    campo_data.click_input(coords=(35, 13))
    time.sleep(0.8)

    print("Apertando ESPAÇO para entrar no campo.")
    pyautogui.press("space")
    time.sleep(0.8)

    print(f"Digitando data no formato robô: {data_emissao}")
    pyautogui.write(data_emissao, interval=0.08)
    time.sleep(0.8)

    print("Pressionando TAB para confirmar.")
    pyautogui.press("tab")
    time.sleep(0.8)


def clicar_botao_nota_fiscal(pedido: dict) -> None:
    data_emissao = str(pedido.get("dtemissao_robo") or "").strip()

    if not data_emissao:
        raise RuntimeError("Data de emissão vazia no pedido.")

    if len(data_emissao) != 6 or not data_emissao.isdigit():
        raise RuntimeError(
            f"Data de emissão inválida para digitação: {data_emissao}. "
            "Esperado formato DDMMAA, exemplo: 220626."
        )

    print(f"Data de Emissão recebida: {data_emissao}")
    preencher_data_emissao(data_emissao)
    print("Data de emissão preenchida.")
