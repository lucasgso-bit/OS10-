"""Handle Agro establishment switching for the OS11 robot.

Close the taxa screen if open, then switch to the target establishment.

Developed by: Giovane Rodrigues
"""

from __future__ import annotations

import time

import pyautogui

from robots.robot_OS11.src.agro_alerts import confirmar_todas_atencoes
from robots.robot_OS11.src.taxa_servico import fechar_tela_taxa_servico_ctrl_f4
from robots.robot_OS11.src.window_utils import (
    focar_janela_por_titulo,
    obter_titulo_janela_ativa,
)


def _formatar_valor_tela(valor: object) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def trocar_estabelecimento(estab: object) -> bool:
    """Close the taxa screen and switch Agro to the target establishment."""
    estab_texto = _formatar_valor_tela(estab)

    if estab_texto == "":
        print("ESTAB vazio. Não foi possível trocar estabelecimento.")
        return False

    print("Trocando estabelecimento para:", estab_texto)

    if not fechar_tela_taxa_servico_ctrl_f4(timeout=1):
        print("Não foi possível fechar a tela de taxa antes da troca de estabelecimento.")
        return False

    focar_janela_por_titulo("AGRO-AG")
    time.sleep(0.8)

    titulo_ativo, classe_ativa = obter_titulo_janela_ativa()
    print("Janela ativa antes do SHIFT+F12:", titulo_ativo, "| Classe:", classe_ativa)

    print("Enviando SHIFT + F12...")
    focar_janela_por_titulo("AGRO-AG")
    time.sleep(0.3)
    pyautogui.hotkey("shift", "f12")
    time.sleep(0.8)

    confirmar_todas_atencoes(timeout_primeira=1.5)
    time.sleep(0.5)

    print("Enviando CTRL + TAB...")
    pyautogui.hotkey("ctrl", "tab")
    time.sleep(0.5)

    titulo_ativo, classe_ativa = obter_titulo_janela_ativa()
    print("Janela ativa antes de digitar ESTAB:", titulo_ativo, "| Classe:", classe_ativa)

    print("Digitando ESTAB:", estab_texto)
    pyautogui.write(estab_texto, interval=0.03)
    time.sleep(0.4)

    for tentativa in range(4):
        print(f"Confirmando ESTAB com ENTER {tentativa + 1}/4...")
        pyautogui.press("enter")
        time.sleep(0.8)
        confirmar_todas_atencoes(timeout_primeira=1.2)

    focar_janela_por_titulo("AGRO-AG")
    time.sleep(0.8)

    print("ESTAB informado com sucesso:", estab_texto)
    return True
