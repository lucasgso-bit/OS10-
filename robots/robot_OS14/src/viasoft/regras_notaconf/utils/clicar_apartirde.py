import time

import pyautogui
import pygetwindow as gw
from pywinauto import Desktop


def buscar_janela_nota_fiscal():
    janelas = gw.getWindowsWithTitle("Nota Fiscal")
    if not janelas:
        raise RuntimeError("Janela Nota Fiscal não encontrada.")
    return janelas[-1]


def clicar_botao_apartirde() -> None:
    janela_gw = buscar_janela_nota_fiscal()
    janela = Desktop(backend="win32").window(handle=janela_gw._hWnd)
    janela.wait("exists", timeout=10)

    botoes = janela.descendants(class_name="TcxButton")

    if not botoes:
        raise RuntimeError("Botão 'À partir de' não encontrado. ClassName=TcxButton")

    print("Clicando no botão À partir de")
    botoes[0].click_input(coords=(116, 12))
    time.sleep(0.8)


def janela_contas_pagar_aberta() -> bool:
    janelas = [
        janela
        for janela in gw.getAllWindows()
        if "lançamento de contas a pagar" in janela.title.lower()
    ]
    return bool(janelas)


def salvar_contas_pagar(max_tentativas: int = 3) -> None:
    for tentativa in range(1, max_tentativas + 1):
        print(f"Tentativa {tentativa}: enviando CTRL + S")

        pyautogui.hotkey("ctrl", "s")
        time.sleep(3)

        if not janela_contas_pagar_aberta():
            print("Tela de lançamento fechou. Salvamento confirmado.")
            return

        print("Tela ainda aberta. Salvamento não confirmado.")

    raise RuntimeError("Falha ao salvar contas a pagar após 3 tentativas.")


def clicar_apartirde(pedido: dict) -> None:
    numero_pedido = str(pedido["num_ped"])

    clicar_botao_apartirde()

    print(f"Digitando número do pedido: {numero_pedido}")
    pyautogui.write(numero_pedido)
    time.sleep(0.8)

    print("Pressionando CTRL + P (Executar)")
    pyautogui.hotkey("ctrl", "p")
    time.sleep(2)

    print("Pressionando ALT + B (Baixar tudo)")
    pyautogui.hotkey("alt", "b")
    time.sleep(0.8)

    salvar_contas_pagar()
