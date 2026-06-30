import time
import unicodedata
from datetime import date, datetime

import pyautogui
import pygetwindow as gw
import pyperclip

from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


def normalizar_titulo(titulo: str) -> str:
    titulo = unicodedata.normalize("NFKD", titulo)
    titulo = "".join(c for c in titulo if not unicodedata.combining(c))
    return titulo.lower().strip()


def buscar_janela_por_titulo(titulo: str, timeout: int = 10):
    titulo_normalizado = normalizar_titulo(titulo)

    for _ in range(timeout):
        for janela in gw.getAllWindows():
            if titulo_normalizado in normalizar_titulo(janela.title):
                return janela
        time.sleep(1)

    return None


def tela_conta_movimento_aberta(timeout: int = 10) -> bool:
    if timeout <= 0:
        return buscar_janela_por_titulo("Conta Movimento", timeout=1) is not None
    return buscar_janela_por_titulo("Conta Movimento", timeout=timeout) is not None


def pressionar_enter(vezes: int, intervalo: float = 0.1) -> None:
    for _ in range(vezes):
        pyautogui.press("enter")
        time.sleep(intervalo)


def preencher_texto(valor: str) -> None:
    pyperclip.copy(str(valor))
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)


def formatar_data_vencimento(valor: str | datetime | date) -> str:
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%d%m%y")
    data = datetime.strptime(str(valor), "%Y-%m-%d %H:%M:%S")
    return data.strftime("%d%m%y")


def confirmar_atencao_se_existir(timeout: int = 3) -> bool:
    janela_atencao = buscar_janela_por_titulo("Atenção", timeout=timeout)

    if janela_atencao is None:
        return False

    print("Tela 'Atenção' encontrada. Confirmando com ENTER.")

    try:
        if janela_atencao.isMinimized:
            janela_atencao.restore()
            time.sleep(0.5)
        janela_atencao.activate()
        time.sleep(0.5)
    except Exception:
        try:
            x_centro = janela_atencao.left + janela_atencao.width // 2
            y_centro = janela_atencao.top + janela_atencao.height // 2
            pyautogui.click(x_centro, y_centro)
            time.sleep(0.5)
        except Exception:
            pass

    pyautogui.press("enter")
    time.sleep(1)
    return True


def preencher_data_vencimento(pedido: dict) -> None:
    dt_venc = formatar_data_vencimento(pedido["venc_dt"])

    print(f"Data de vencimento formatada para digitação: {dt_venc}")

    pyautogui.write(dt_venc, interval=0.03)
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(1)

    atencao_confirmada = confirmar_atencao_se_existir(timeout=3)

    if atencao_confirmada:
        print("Tela Atenção apareceu após preencher vencimento. Aviso confirmado.")
    else:
        print("Data de vencimento preenchida sem tela de Atenção.")


def montar_descricao_pagamento(pedido: dict) -> str:
    tipo_pgto = str(pedido["tipopgto"]).strip().upper()

    if tipo_pgto == "D":
        banco = str(pedido.get("banco", "")).strip()
        agencia = str(pedido.get("agencia", "")).strip()
        conta = str(pedido.get("conta", "")).strip()
        return f"Banco: {banco}, Ag.: {agencia}, Cc.: {conta}"

    if tipo_pgto == "B":
        return str(pedido.get("chaveboleto", "")).strip()

    if tipo_pgto == "P":
        return str(pedido.get("pix", "")).strip()

    if tipo_pgto == "A":
        return "À vista"

    raise ValueError(f"TIPOPGTO não mapeado para Conta Movimento: {tipo_pgto}")


def salvar_conta_movimento() -> None:
    pyautogui.hotkey("ctrl", "s")
    time.sleep(2)


def aguardar_tela_conta_movimento_fechar(timeout: int = 10) -> bool:
    inicio = time.time()
    while time.time() - inicio < timeout:
        if not tela_conta_movimento_aberta(timeout=0):
            return True
        time.sleep(0.5)
    return False


def preencher_conta_movimento(pedido: dict) -> None:
    print("Pressionando ALT + A, para abrir a tela de acerto financeiro")
    pyautogui.hotkey("alt", "a")

    print("Verificando tela Conta Movimento...")
    time.sleep(1)

    if not tela_conta_movimento_aberta(timeout=10):
        raise RuntimeError("Tela 'Conta Movimento' não abriu.")

    focar_janela_por_titulo("Conta Movimento", timeout=10)
    time.sleep(1)

    print("Preenchendo conta movimento: AFGR")
    preencher_texto("AFGR")

    pressionar_enter(6)

    preencher_data_vencimento(pedido)

    pressionar_enter(6)

    descricao_pagamento = montar_descricao_pagamento(pedido)
    print(f"Preenchendo descrição do pagamento: {descricao_pagamento}")
    preencher_texto(descricao_pagamento)

    time.sleep(0.5)

    print("Salvando Conta Movimento com CTRL + S")
    salvar_conta_movimento()

    aguardar_tela_conta_movimento_fechar()
    print("Tela Conta Movimento preenchida e salva.")
