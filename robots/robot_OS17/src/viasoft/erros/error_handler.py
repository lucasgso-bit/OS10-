import traceback

import pyautogui


def tratar_erro_pedido(pedido: dict, erro: Exception, etapa: str) -> str:
    """Take a screenshot and print error info. Returns screenshot path."""
    screenshot_path = f"erro_OS17_{pedido.get('numerocm', 'unknown')}_{etapa}.png"

    try:
        pyautogui.screenshot(screenshot_path)
    except Exception:
        screenshot_path = None

    print(f"[OS17] ERRO na etapa '{etapa}' para pedido {pedido.get('numerocm')}:")
    print(f"  ESTAB: {pedido.get('estab')}")
    print(f"  IE: {pedido.get('ins_estad')}")
    print(f"  Erro: {erro}")
    traceback.print_exc()

    return screenshot_path
