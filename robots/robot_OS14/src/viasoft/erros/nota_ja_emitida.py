import time
import unicodedata
from datetime import datetime
from pathlib import Path

import pyautogui
import pygetwindow as gw


SCREENSHOT_DIR = Path("logs/screenshots")


def normalizar_titulo(titulo: str) -> str:
    titulo = unicodedata.normalize("NFKD", titulo)
    titulo = "".join(c for c in titulo if not unicodedata.combining(c))
    return titulo.lower().strip()


def buscar_janela_por_titulo(titulo: str, timeout: int = 3):
    titulo_normalizado = normalizar_titulo(titulo)

    for _ in range(timeout):
        for janela in gw.getAllWindows():
            if titulo_normalizado in normalizar_titulo(janela.title):
                return janela
        time.sleep(1)

    return None


def focar_janela_segura(janela) -> None:
    try:
        if janela.isMinimized:
            janela.restore()
            time.sleep(0.5)
        janela.activate()
        time.sleep(1)
    except Exception:
        try:
            x_centro = janela.left + janela.width // 2
            y_centro = janela.top + janela.height // 2
            pyautogui.click(x_centro, y_centro)
            time.sleep(1)
        except Exception:
            pass


def salvar_screenshot_nota_ja_emitida(pedido: dict) -> Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    estab = str(pedido.get("estab", "sem_estab")).strip()
    num_ped = str(pedido.get("num_ped", "sem_pedido")).strip()

    caminho = SCREENSHOT_DIR / f"nota_ja_emitida_estab_{estab}_pedido_{num_ped}_{data_hora}.png"
    pyautogui.screenshot(str(caminho))
    return caminho


def validar_nota_ja_emitida(timeout: int = 3) -> None:
    janela_atencao = buscar_janela_por_titulo("Atenção", timeout=timeout)

    if janela_atencao is None:
        return

    print("Tela 'Atenção' encontrada após preencher chave NF.")
    print("Possível nota já emitida.")

    focar_janela_segura(janela_atencao)
    time.sleep(4)

    print("Erro, imagem enviada via email, sistema vai reiniciar")

    raise RuntimeError("Nota já emitida ou tela de Atenção aberta após preencher chave NF.")
