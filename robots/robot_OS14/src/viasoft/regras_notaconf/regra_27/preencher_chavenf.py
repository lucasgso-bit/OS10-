import time
import unicodedata

import pyautogui
import pygetwindow as gw

from robots.robot_OS14.src.viasoft.erros.nota_ja_emitida import validar_nota_ja_emitida


TIMEOUT_SELECAO_ENDERECO = 10
DELAY_CURTO = 0.3
DELAY_MEDIO = 0.7
DELAY_LONGO = 1.5


def normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto.lower().strip()


def obter_janela_selecao_endereco():
    for janela in gw.getAllWindows():
        titulo = normalizar_texto(janela.title)
        if "selecao" in titulo and "endereco" in titulo:
            return janela
    return None


def tela_selecao_endereco_aberta() -> bool:
    return obter_janela_selecao_endereco() is not None


def aguardar_tela_selecao_endereco(timeout: int = TIMEOUT_SELECAO_ENDERECO) -> bool:
    inicio = time.time()
    while time.time() - inicio < timeout:
        if tela_selecao_endereco_aberta():
            return True
        time.sleep(0.5)
    return False


def focar_tela_selecao_endereco(timeout: int = TIMEOUT_SELECAO_ENDERECO) -> None:
    inicio = time.time()
    while time.time() - inicio < timeout:
        janela = obter_janela_selecao_endereco()
        if janela:
            if janela.isMinimized:
                janela.restore()
                time.sleep(DELAY_MEDIO)
            janela.activate()
            time.sleep(DELAY_LONGO)
            return
        time.sleep(0.5)
    raise RuntimeError("Tela Seleção de Endereço não encontrada para foco.")


def confirmar_filtro_endereco() -> None:
    time.sleep(DELAY_MEDIO)
    if tela_selecao_endereco_aberta():
        pyautogui.press("enter")
        time.sleep(DELAY_LONGO)


def preencher_cnpj_fornecedor(cnpj_fornecedor: str) -> None:
    cnpj_fornecedor = str(cnpj_fornecedor or "").strip()

    if not cnpj_fornecedor:
        raise RuntimeError("CNPJ do fornecedor vazio para seleção de endereço.")

    print(f"Preenchendo filtro por CNPJ: {cnpj_fornecedor}")

    focar_tela_selecao_endereco()

    for _ in range(6):
        pyautogui.press("right")
        time.sleep(0.2)

    pyautogui.press("up")
    time.sleep(DELAY_CURTO)

    pyautogui.write(cnpj_fornecedor)
    time.sleep(DELAY_LONGO)

    confirmar_filtro_endereco()


def preencher_filtro_ie(ie_fornecedor: str) -> None:
    ie_fornecedor = str(ie_fornecedor or "").strip()

    if not ie_fornecedor:
        raise RuntimeError("IE do fornecedor vazio para seleção de endereço.")

    print(f"Preenchendo filtro por IE: {ie_fornecedor}")

    focar_tela_selecao_endereco()

    for _ in range(2):
        pyautogui.press("right")
        time.sleep(0.2)

    pyautogui.press("up")
    time.sleep(DELAY_CURTO)

    pyautogui.write(ie_fornecedor)
    time.sleep(DELAY_LONGO)

    confirmar_filtro_endereco()


def tratar_selecao_endereco(pedido: dict) -> None:
    if not aguardar_tela_selecao_endereco():
        print("Tela Seleção de Endereço não abriu.")
        return

    focar_tela_selecao_endereco()

    ie_fornecedor = str(pedido.get("ie_fornecedor") or "").strip()
    cnpj_fornecedor = str(pedido.get("cnpjf_fornecedor") or "").strip()

    print(f"Recebi o IE do fornecedor: {ie_fornecedor}")
    print(f"Recebi o CNPJ do fornecedor: {cnpj_fornecedor}")

    if ie_fornecedor:
        preencher_filtro_ie(ie_fornecedor)
    elif cnpj_fornecedor:
        preencher_cnpj_fornecedor(cnpj_fornecedor)
    else:
        raise RuntimeError("Pedido sem IE e sem CNPJ para seleção de endereço.")

    time.sleep(2)

    if tela_selecao_endereco_aberta():
        print("Tela Seleção de Endereço ainda aberta. Tentando confirmar novamente.")
        pyautogui.press("enter")
        time.sleep(2)

    print("Tratamento da seleção de endereço finalizado.")


def preencher_chave_nf(pedido: dict) -> None:
    chave_nf = str(pedido.get("chavchavenf") or "").strip()

    if not chave_nf:
        raise RuntimeError("Chave NF vazia no pedido.")

    print("Iniciando preenchimento da chave NF.")
    pyautogui.write(chave_nf)
    time.sleep(0.5)

    print("Confirmando chave NF.")
    pyautogui.press("enter", presses=3, interval=0.3)
    time.sleep(1)

    print("Navegando após chave NF.")
    pyautogui.press("right")
    time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(2)

    print("Tratando seleção de endereço.")
    tratar_selecao_endereco(pedido)

    print("Validando nota já emitida.")
    validar_nota_ja_emitida(timeout=3)

    print("Step preencher_chave_nf finalizado.")
