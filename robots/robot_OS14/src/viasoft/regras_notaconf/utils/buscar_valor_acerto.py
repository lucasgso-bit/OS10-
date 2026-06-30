import time

import pyautogui
import pygetwindow as gw
from pywinauto import Desktop

from robots.robot_OS14.src.viasoft.viasoft_janela import focar_janela_por_titulo


CLASS_NAME_VALOR_ACERTO = "TVsNumRight"
INSTANCE_VALOR_ACERTO = 1


def buscar_janela_nota_fiscal():
    janelas = gw.getWindowsWithTitle("Nota Fiscal")
    if not janelas:
        raise RuntimeError("Janela Nota Fiscal não encontrada.")
    return janelas[-1]


def obter_janela_nota_fiscal_pywinauto():
    janela_gw = buscar_janela_nota_fiscal()
    janela = Desktop(backend="win32").window(handle=janela_gw._hWnd)
    janela.wait("exists", timeout=10)
    return janela


def coletar_valor_acerto() -> str:
    janela = obter_janela_nota_fiscal_pywinauto()
    campos_valor = janela.descendants(class_name=CLASS_NAME_VALOR_ACERTO)

    if len(campos_valor) < INSTANCE_VALOR_ACERTO:
        raise RuntimeError(
            f"Campo de valor do acerto não encontrado. "
            f"ClassName={CLASS_NAME_VALOR_ACERTO} | "
            f"Instance={INSTANCE_VALOR_ACERTO} | "
            f"Total encontrado={len(campos_valor)}"
        )

    campo_valor = campos_valor[INSTANCE_VALOR_ACERTO - 1]
    valor = str(campo_valor.window_text()).strip()

    if not valor:
        raise RuntimeError(
            f"Campo de valor do acerto foi encontrado, mas retornou vazio. "
            f"ClassName={CLASS_NAME_VALOR_ACERTO} | Instance={INSTANCE_VALOR_ACERTO}"
        )

    print(
        f"Campo de valor localizado: "
        f"ClassName={campo_valor.element_info.class_name} | Texto={repr(valor)}"
    )
    return valor


def normalizar_valor_tela(valor: str | float | int) -> float:
    valor = (
        str(valor).strip()
        .replace("R$", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", ".")
        .strip()
    )

    return round(float(valor), 2)


def buscar_valor_acerto(pedido: dict) -> float:
    valor_total = pedido["valortotal"]

    focar_janela_por_titulo("Nota Fiscal", timeout=60)
    time.sleep(1)

    pyautogui.hotkey("alt", "t")
    time.sleep(2)

    valor_coletado = coletar_valor_acerto()
    print(f"Valor coletado bruto: {repr(valor_coletado)}")

    valor_coletado_convertido = normalizar_valor_tela(valor_coletado)
    valor_total_convertido = round(float(valor_total), 2)

    if valor_coletado_convertido != valor_total_convertido:
        raise RuntimeError(
            f"Valor divergente. Tela={valor_coletado_convertido} | SQL={valor_total_convertido}"
        )

    print(f"Valor coletado e valor total são iguais: {valor_coletado_convertido}")
    return valor_coletado_convertido
