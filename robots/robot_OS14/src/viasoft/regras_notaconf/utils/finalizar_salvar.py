import time

import pyautogui
import pygetwindow as gw

from robots.robot_OS14.src.viasoft.erros.erro_de_atualizacao import validar_tela_erro_de_atualizacao
from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def tela_acerto_financeiro_aberta() -> bool:
    janelas = [
        janela
        for janela in gw.getAllWindows()
        if "acerto financeiro" in janela.title.lower()
    ]
    return bool(janelas)


def tela_nota_fiscal_aberta() -> bool:
    janelas = [
        janela
        for janela in gw.getAllWindows()
        if "nota fiscal" in janela.title.lower()
    ]
    return bool(janelas)


def enviar_ctrl_s() -> None:
    pyautogui.hotkey("ctrl", "s")
    time.sleep(3)


def finalizar_fluxo(pedido: dict) -> None:
    print("Verificando tela de Acerto Financeiro...")

    if not tela_acerto_financeiro_aberta():
        raise RuntimeError("Tela 'Acerto Financeiro' não encontrada.")

    focar_janela_por_titulo("Acerto Financeiro", timeout=30)

    print("Enviando CTRL + S no Acerto Financeiro")
    enviar_ctrl_s()

    if tela_acerto_financeiro_aberta():
        raise RuntimeError("Tela 'Acerto Financeiro' não fechou após CTRL + S.")

    print("Acerto Financeiro finalizado.")
    print("Focando na Nota Fiscal...")

    focar_janela_por_titulo("Nota Fiscal", timeout=30)

    print("Enviando CTRL + S na Nota Fiscal")
    enviar_ctrl_s()

    time.sleep(10)

    validar_tela_erro_de_atualizacao(pedido, timeout=3)

    pyautogui.hotkey("ctrl", "f4")

    print("Fluxo finalizado com sucesso.")
