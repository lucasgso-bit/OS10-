"""OS20 — Nota Fiscal launch automation for NOTACONF 65.

Navigates Agro to the note entry form and opens a new record typed as
NOTACONF 65. Field filling is left for the caller to implement.
"""

from __future__ import annotations

import time
from typing import Any

import pyautogui

from robots.robot_OS20.src.agro_estab import focus_window, wait_window_startswith


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def lancar_nota_65(nota: dict[str, Any], itens: list[dict[str, Any]]) -> bool:
    """Open the Agro note entry screen for NOTACONF 65 and position the cursor.

    Args:
        nota: header row from buscar_notas_para_lancar() — contains NUMEROCM,
              NUMERO_NOTA, SERIE, CHAVE_ACESSO, ESTAB, CFOP, VALOR_TOTAL, etc.
        itens: all rows for this NUMERO_NOTA (one per NCM/ITEM combination),
               each with ITEM, DESCRICAO, NCM, QUANTIDADE, VALOR_UNITARIO, etc.

    Returns:
        True when the entry form opened successfully; False on navigation failure.

    Navigation sequence (mirrors NOTACONF 225 in OS07):
        1. Focus main AGRO-AG window
        2. Alt+N → Enter         → open Nota Fiscal menu item
        3. Wait "Filtrar NF"
        4. Alt+V                 → open/view record list
        5. Wait "Nota Fiscal"
        6. Ctrl+Insert           → create new record
        7. Type "65" → Enter     → select NOTACONF
        8. Wait for entry form   ← caller continues from here
    """
    numero_nota = str(nota.get("NUMERO_NOTA") or "").strip()
    serie = str(nota.get("SERIE") or "").strip()
    cfop = str(nota.get("CFOP") or "").strip()
    estab = str(nota.get("ESTAB") or "").strip()

    print(f"[OS20] Lançando nota {numero_nota} série {serie} | estab {estab} | CFOP {cfop}")
    print(f"[OS20] {len(itens)} item(ns): {[i.get('ITEM') for i in itens]}")

    # 1. Foca janela principal
    if not focus_window("AGRO-AG"):
        print("[OS20] Janela AGRO-AG não encontrada.")
        return False

    # 2. Abre menu Nota Fiscal (Alt+N → Enter)
    pyautogui.hotkey("alt", "n")
    _sleep(1)
    pyautogui.press("enter")
    _sleep(1)

    # 3. Aguarda tela de filtro
    if not (
        wait_window_startswith("Filtrar NF - Cabeçalho", timeout_seconds=6)
        or wait_window_startswith("Filtrar NF", timeout_seconds=3)
        or wait_window_startswith("Filtrar", timeout_seconds=3)
    ):
        print("[OS20] Tela de filtro NF não apareceu.")
        return False

    # 4. Abre a lista de notas (Alt+V)
    pyautogui.hotkey("alt", "v")
    _sleep(1)

    # 5. Aguarda tela Nota Fiscal
    if not (
        wait_window_startswith("Nota Fiscal", timeout_seconds=10)
        or wait_window_startswith("Nota", timeout_seconds=5)
    ):
        print("[OS20] Tela 'Nota Fiscal' não carregou.")
        return False

    # 6. Novo registro (Ctrl+Insert)
    pyautogui.hotkey("ctrl", "insert")
    _sleep(5)

    # 7. Digita NOTACONF 65 e confirma
    pyautogui.write("65", interval=0.03)
    pyautogui.press("enter")
    _sleep(3)

    # -------------------------------------------------------------------------
    # TODO: implementar preenchimento dos campos da nota a partir daqui
    #
    # Dados disponíveis em `nota`:
    #   nota["NUMEROCM"]      — código do cadastro de movimentação
    #   nota["NUMERO_NOTA"]   — número da nota fiscal
    #   nota["SERIE"]         — série da nota
    #   nota["CHAVE_ACESSO"]  — chave de acesso NF-e
    #   nota["ESTAB"]         — estabelecimento
    #   nota["CFOP"]          — CFOP (dentro/fora UF já resolvido)
    #   nota["VALOR_TOTAL"]   — valor total da nota
    #   nota["VALOR_UNITARIO"]— valor unitário médio
    #
    # Dados disponíveis em cada `item` de `itens`:
    #   item["ITEM"]          — código do item no Agro
    #   item["NCM"]           — NCM
    #   item["DESCRICAO"]     — descrição
    #   item["QUANTIDADE"]    — quantidade
    #   item["VALOR_UNITARIO"]— valor unitário do item
    #   item["VALOR_TOTAL"]   — valor total do item
    # -------------------------------------------------------------------------

    print(f"[OS20] Tela de lançamento NOTACONF 65 aberta para nota {numero_nota}.")
    return True
