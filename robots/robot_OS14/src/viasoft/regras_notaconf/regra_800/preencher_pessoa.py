import time

import pyautogui
import pygetwindow as gw

from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def tela_selecao_endereco_aberta() -> bool:
    janelas = [
        janela
        for janela in gw.getAllWindows()
        if "seleção de endereço" in janela.title.lower()
    ]
    return bool(janelas)


def preencher_cnpj_fornecedor(cnpj_fornecedor: str) -> None:
    for _ in range(6):
        pyautogui.press("right")
        time.sleep(0.2)

    pyautogui.press("up")
    time.sleep(0.2)

    pyautogui.write(str(cnpj_fornecedor))
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(1)


def preencher_filtro_ie(ie_fornecedor: str) -> None:
    for _ in range(2):
        pyautogui.press("right")
        time.sleep(0.1)

    pyautogui.press("up")
    time.sleep(0.2)

    pyautogui.write(str(ie_fornecedor))
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(1)


def tratar_selecao_endereco(pedido: dict) -> None:
    if not tela_selecao_endereco_aberta():
        return

    focar_janela_por_titulo("Seleção de Endereço", timeout=10)

    ie_fornecedor = pedido.get("ie_fornecedor")
    print(f"Recebi o ie do fornecedor: {ie_fornecedor}")
    cnpj_fornecedor = pedido.get("cnpjf_fornecedor")
    print(f"Recebi o cnpj do fornecedor: {cnpj_fornecedor}")

    if ie_fornecedor is None or str(ie_fornecedor).strip() == "":
        preencher_cnpj_fornecedor(cnpj_fornecedor)
    else:
        preencher_filtro_ie(ie_fornecedor)


def preencher_pessoa(pedido: dict) -> None:
    fornecedor = str(pedido["fornecedor"])

    time.sleep(0.5)

    pyautogui.write(fornecedor)
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(1)

    tratar_selecao_endereco(pedido)
