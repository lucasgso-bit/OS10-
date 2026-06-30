import time
import unicodedata

import pyautogui
import pygetwindow as gw
from pywinauto import Desktop

from robots.robot_OS14.src.viasoft.erros.tela_valores_pendentes import validar_tela_valores_pendentes
from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def normalizar_titulo(titulo: str) -> str:
    titulo = unicodedata.normalize("NFKD", titulo)
    titulo = "".join(c for c in titulo if not unicodedata.combining(c))
    return titulo.lower().strip()


def confirmar_atencao_se_existir(timeout: int = 3) -> bool:
    atencao = buscar_janela_por_titulo("Atenção", timeout=timeout)

    if atencao is None:
        return False

    print("Tela 'Atenção' encontrada. Confirmando com ENTER.")

    try:
        if atencao.isMinimized:
            atencao.restore()
            time.sleep(0.5)
        atencao.activate()
        time.sleep(0.5)
    except Exception:
        try:
            x_centro = atencao.left + atencao.width // 2
            y_centro = atencao.top + atencao.height // 2
            pyautogui.click(x_centro, y_centro)
            time.sleep(0.5)
        except Exception:
            pass

    pyautogui.press("enter")
    time.sleep(1)
    return True


def buscar_janela_por_titulo(titulo: str, timeout: int = 10):
    titulo_normalizado = normalizar_titulo(titulo)

    for _ in range(timeout):
        for janela in gw.getAllWindows():
            if titulo_normalizado in normalizar_titulo(janela.title):
                return janela
        time.sleep(1)

    return None


def tela_pagamento_duplicatas_aberta(timeout: int = 10) -> bool:
    return buscar_janela_por_titulo("Pagamento com Duplicatas", timeout=timeout) is not None


def pressionar_alt_a() -> None:
    pyautogui.hotkey("alt", "a")


def clicar_regiao_pagamento() -> None:
    janela = buscar_janela_por_titulo("Pagamento com Duplicatas", timeout=10)

    if janela is None:
        raise RuntimeError("Tela 'Pagamento com Duplicatas' não encontrada.")

    janela_pywinauto = Desktop(backend="win32").window(handle=janela._hWnd)
    janela_pywinauto.wait("exists", timeout=10)

    grids = janela_pywinauto.children(class_name="TVsStringGrid")
    total_grids = len(grids)

    print(f"Total de grids TVsStringGrid encontrados: {total_grids}")

    if total_grids == 0:
        raise RuntimeError("Grid de pagamento não encontrado. ClassName=TVsStringGrid")

    if total_grids > 1:
        raise RuntimeError(
            f"Mais de um grid encontrado na tela 'Pagamento com Duplicatas'. "
            f"Total encontrado: {total_grids}. "
            "Processo bloqueado para evitar preenchimento no grid errado."
        )

    grids[0].click_input(coords=(80, 27))
    time.sleep(1)


def navegar_direita(vezes: int) -> None:
    for _ in range(vezes):
        pyautogui.press("right")
        time.sleep(0.05)


def preencher_campo(valor: str, descricao: str = "campo") -> None:
    print(f"Preenchendo {descricao}: {valor}")

    pyautogui.write(str(valor), interval=0.03)
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(1)

    atencao_confirmada = confirmar_atencao_se_existir(timeout=2)

    if atencao_confirmada:
        print(f"Tela Atenção apareceu após preencher {descricao}. Aviso confirmado.")
        focar_janela_por_titulo("Pagamento com Duplicatas", timeout=10)
        time.sleep(0.5)
        return

    print(f"{descricao} preenchido sem tela de Atenção.")


def preencher_boleto(pedido: dict) -> None:
    navegar_direita(13)
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    preencher_campo(pedido["chaveboleto"], descricao="chave do boleto")


def preencher_deposito(pedido: dict) -> None:
    navegar_direita(14)
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    confirmar_atencao_se_existir(timeout=2)
    preencher_campo(pedido["banco"], descricao="banco")
    pyautogui.press("enter")
    preencher_campo(pedido["agencia"], descricao="agência")
    preencher_campo(pedido["conta"], descricao="conta")


def preencher_pix(pedido: dict) -> None:
    navegar_direita(30)
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    preencher_campo("3", descricao="tipo de PIX")
    preencher_campo(pedido["pix"], descricao="chave PIX")


def salvar_pagamento(max_tentativas: int = 3) -> None:
    for tentativa in range(1, max_tentativas + 1):
        print(f"Tentativa {tentativa}: salvando pagamento com CTRL + S")

        pyautogui.keyDown("ctrl")
        time.sleep(0.2)
        pyautogui.press("s")
        time.sleep(0.2)
        pyautogui.keyUp("ctrl")

        time.sleep(2)

        atencao_confirmado = confirmar_atencao_se_existir(timeout=3)
        if atencao_confirmado:
            print("Aviso confirmado, opção Sim selecionada")
            time.sleep(2)

        if not tela_pagamento_duplicatas_aberta():
            print("Pagamento salvo. Tela fechou.")
            return

        print("Tela ainda aberta. Tentando novamente.")

    raise RuntimeError("Falha ao salvar 'Pagamento com Duplicatas' após 3 tentativas.")


def executar_acerto_financeiro(pedido: dict) -> None:
    tipo_pgto = str(pedido["tipopgto"]).strip().upper()

    focar_janela_por_titulo("Nota Fiscal", timeout=30)

    pressionar_alt_a()
    time.sleep(2)

    validar_tela_valores_pendentes(pedido, timeout=3)

    if not tela_pagamento_duplicatas_aberta():
        raise RuntimeError("Tela 'Pagamento com Duplicatas' não abriu.")

    focar_janela_por_titulo("Pagamento com Duplicatas", timeout=30)
    clicar_regiao_pagamento()

    if tipo_pgto == "B":
        preencher_boleto(pedido)
    elif tipo_pgto == "D":
        preencher_deposito(pedido)
    elif tipo_pgto == "P":
        preencher_pix(pedido)
    elif tipo_pgto == "A":
        print("Tipo de pagamento A. Nenhuma ação financeira necessária.")
    else:
        raise ValueError(f"TIPOPGTO não mapeado: {tipo_pgto}")

    salvar_pagamento()
