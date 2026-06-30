import traceback
from datetime import datetime
from pathlib import Path

import pyautogui


def capturar_screenshot(pedido: dict) -> Path:
    pasta = Path("logs/screenshots")
    pasta.mkdir(parents=True, exist_ok=True)

    data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    pedido_id = pedido.get("pedido", "sem_pedido")

    caminho = pasta / f"erro_{pedido_id}_{data_hora}.png"

    imagem = pyautogui.screenshot()
    imagem.save(caminho)

    return caminho


def tratar_erro_pedido(
    pedido: dict,
    erro: Exception,
    etapa: str,
) -> None:
    screenshot_path = capturar_screenshot(pedido)

    print("=" * 80)
    print("ERRO NO PROCESSAMENTO DO PEDIDO")
    print(f"Etapa: {etapa}")
    print(f"Pedido: {pedido.get('pedido')}")
    print(f"Estab: {pedido.get('estab')}")
    print(f"Erro: {erro}")
    print(f"Screenshot: {screenshot_path}")
    print(traceback.format_exc())
    print("=" * 80)
