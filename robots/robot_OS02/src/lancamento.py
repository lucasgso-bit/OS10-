"""OS02 — Nota Fiscal launch automation for NOTACONF 162.

Navigates Agro to the NOTACONF 162 entry form, fills in the access key,
waits for the NF-e data screen to load, then fills each item line
(item code, quantity, unit value, CFOP) and saves with Ctrl+S.

Developed by: MATHEUS CORREA
Updated by: MATHEUS CORREA
Last Modified: 2026-06-22
Version: 4.0.0
"""

from __future__ import annotations

import time
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import pyautogui
import pygetwindow as gw

from robots.robot_OS02.src.agro_estab import focus_window, wait_window_startswith


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _fmt_data(valor: Any) -> str:
    """Convert a date value to ddmmyy digits."""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%d%m%y")

    texto = str(valor).strip()

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(texto, fmt).strftime("%d%m%y")
        except ValueError:
            continue

    digitos = "".join(c for c in texto if c.isdigit())

    if len(digitos) >= 8:
        # Caso venha como yyyymmdd, exemplo: 20260623 -> 230626
        if digitos[:4].startswith(("19", "20")):
            return f"{digitos[6:8]}{digitos[4:6]}{digitos[2:4]}"

        # Caso venha como ddmmyyyy, exemplo: 23062026 -> 230626
        return f"{digitos[:4]}{digitos[6:8]}"

    return digitos[:6]


def _fmt_valor(valor: Any) -> str:
    """Format a numeric value to 4 decimal places using a comma separator."""
    try:
        d = Decimal(str(valor)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except Exception:
        return str(valor)
    return str(d).replace(".", ",")


def _fmt_quantidade(valor: Any) -> str:
    """Format a numeric value to 2 decimal places using a comma separator."""
    try:
        d = Decimal(str(valor)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except Exception:
        return str(valor)
    return str(d).replace(".", ",")


def _checar_erro_popup() -> bool:
    """Dismiss any open Advertências/error window and return True if a critical row was found."""
    for window in gw.getAllWindows():
        title = window.title.strip()
        if title.startswith("[A]dvertências") or title.startswith("[A]dvertencias"):
            if _advertencias_tem_erro_critico():
                print("[OS02] Erro crítico detectado na janela de Advertências.")
                pyautogui.press("escape")
                _sleep(0.5)
                return True
            pyautogui.hotkey("alt", "o")
            _sleep(0.5)
    return False


def _advertencias_tem_erro_critico() -> bool:
    """Return True if the Advertências window has a red error row.

    Captures a screenshot of the window's list area and scans for any
    red pixel (r>150, g<80, b<80) indicating an '(I) Inconsistência' row.
    Uses a region screenshot (single capture) instead of per-pixel calls
    to avoid missing red text pixels when the background is white/cream.
    """
    for window in gw.getAllWindows():
        title = window.title.strip()
        if title.startswith("[A]dvertências") or title.startswith("[A]dvertencias"):
            left = window.left + 5
            top = window.top + 28
            width = max(1, min(window.width - 10, 600))
            height = 80
            img = pyautogui.screenshot(region=(left, top, width, height))
            for y in range(0, img.height, 2):
                for x in range(0, img.width, 3):
                    r, g, b = img.getpixel((x, y))
                    if r > 150 and g < 80 and b < 80:
                        return True
    return False


def lancar_nota_162(
    nota: dict[str, Any],
    itens: list[dict[str, Any]],
    *,
    is_first_note: bool = True,
    close_form: bool = True,
) -> bool:
    """Open the NOTACONF 162 entry screen and fill all item lines.

    is_first_note=True  — navigate from AGRO-AG through the menu, press
                          Ctrl+Insert and type '162' to open the entry form.
    is_first_note=False — the caller already pressed Ctrl+Insert (same estab,
                          continuing from the previous note); just wait for the
                          'Dados da NF-e Recebida' form to appear.

    close_form=True  — close the entry form with Ctrl+F4 after saving
                       (used when switching estab or on the last note).
    close_form=False — leave the form open after saving; the caller will
                       press Ctrl+Insert to create the next record.

    Returns True on success, False on any failure.
    """
    numero_nota = str(nota.get("NUMERO_NOTA") or "").strip()
    serie = str(nota.get("SERIE") or "").strip()
    chave_acesso = str(nota.get("CHAVE_ACESSO") or "").strip()
    estab = str(nota.get("ESTAB") or "").strip()
    data_emissao = _fmt_data(nota.get("DATA_EMISSAO") or "")

    print(
        f"[OS02] Lançando nota {numero_nota} série {serie} | estab {estab} | "
        f"{len(itens)} item(ns): {[i.get('ITEM') for i in itens]}"
    )

    if is_first_note:
        # ------------------------------------------------------------------
        # 1. Focus main AGRO-AG window
        # ------------------------------------------------------------------
        if not focus_window("AGRO-AG"):
            print("[OS02] Janela AGRO-AG não encontrada.")
            return False

        # ------------------------------------------------------------------
        # 2. Open Nota Fiscal menu (Alt+N → Enter)
        # ------------------------------------------------------------------
        pyautogui.hotkey("alt", "n")
        _sleep(1)
        pyautogui.press("enter")
        _sleep(1)

        # ------------------------------------------------------------------
        # 3. Wait for filter screen
        # ------------------------------------------------------------------
        if not (
            wait_window_startswith("Filtrar NF - Cabeçalho", timeout_seconds=6)
            or wait_window_startswith("Filtrar NF", timeout_seconds=3)
            or wait_window_startswith("Filtrar", timeout_seconds=3)
        ):
            print("[OS02] Tela de filtro NF não apareceu.")
            return False

        # ------------------------------------------------------------------
        # 4. Open note list (Alt+V)
        # ------------------------------------------------------------------
        pyautogui.hotkey("alt", "v")
        _sleep(1)

        # ------------------------------------------------------------------
        # 5. Wait for Nota Fiscal list screen
        # ------------------------------------------------------------------
        if not (
            wait_window_startswith("Nota Fiscal", timeout_seconds=10)
            or wait_window_startswith("Nota", timeout_seconds=5)
        ):
            print("[OS02] Tela 'Nota Fiscal' não carregou.")
            return False

        # ------------------------------------------------------------------
        # 6. New record (Ctrl+Insert) → type 162 → Enter
        # ------------------------------------------------------------------
        pyautogui.hotkey("ctrl", "insert")
        _sleep(6)

        pyautogui.write("162", interval=0.03)
        pyautogui.press("enter")
        _sleep(3)
    else:
        # Caller already pressed Ctrl+Insert and waited 6s.
        # Complete the record type selection: type 162 → Enter.
        pyautogui.write("162", interval=0.03)
        pyautogui.press("enter")
        _sleep(3)

    # ------------------------------------------------------------------
    # 7. Wait for "Dados da NF-e Recebida" window
    # ------------------------------------------------------------------
    if not wait_window_startswith("Dados da NF-e Recebida", timeout_seconds=10):
        print("[OS02] Tela 'Dados da NF-e Recebida' não apareceu.")
        return False

    if not focus_window("Dados da NF-e Recebida"):
        print("[OS02] Não foi possível focar 'Dados da NF-e Recebida'.")
        return False

    # ------------------------------------------------------------------
    # 8. Type CHAVE_ACESSO → right×3 → Enter
    # ------------------------------------------------------------------
    if not chave_acesso:
        print("[OS02] CHAVE_ACESSO não encontrada na nota.")
        return False

    pyautogui.write(chave_acesso, interval=0.02)
    _sleep(1)
    pyautogui.press("enter")
    _sleep(2)
    # 656-Rejeição: Consumo Indevido — AGRO queries SEFAZ after chave entry; dismiss and continue
    if wait_window_startswith("Atenção", timeout_seconds=3):
        print("[OS02] Popup 'Atenção' após chave — descartando e continuando.")
        pyautogui.press("enter")
        _sleep(0.5)
    pyautogui.press("enter")
    _sleep(1)
    pyautogui.press("enter")
    _sleep(1)
    pyautogui.press("right", interval=0.2)
    _sleep(0.3)
    pyautogui.press("enter")
    _sleep(1)

    if _checar_erro_popup():
        print(
            f"[OS02] Erro detectado após inserção da chave — abortando nota {numero_nota}."
        )
        return False

    # ------------------------------------------------------------------
    # 9. Date field on new screen → 11 Enters to reach item code field
    # ------------------------------------------------------------------
    _sleep(2)

    pyautogui.hotkey("alt", "o")
    _sleep(0.7)

    pyautogui.hotkey("alt", "o")
    _sleep(0.7)

    pyautogui.hotkey("alt", "p")
    _sleep(0.7)

    pyautogui.hotkey("alt", "o")
    _sleep(0.7)

    print(f"[OS02] Data emissão: {data_emissao}")

    pyautogui.write(str(data_emissao), interval=0.03)
    _sleep(0.3)
    pyautogui.press("enter", presses=11, interval=0.3)
    _sleep(0.5)

    # ------------------------------------------------------------------
    # 10. Fill each item line
    # ------------------------------------------------------------------
    for idx, item in enumerate(itens):
        codigo_item = str(item.get("ITEM") or "").strip()
        quantidade = _fmt_quantidade(item.get("QUANTIDADE") or "").strip()
        valor_unitario = _fmt_valor(item.get("VALOR_UNITARIO") or "0")
        cfop = str(item.get("CFOP") or nota.get("CFOP") or "").strip()

        print(
            f"[OS02] Item {idx + 1}/{len(itens)}: "
            f"codigo={codigo_item} qtd={quantidade} vunit={valor_unitario} cfop={cfop}"
        )
        _sleep(1)
        # a. Item code → Enter → Enter
        pyautogui.write(codigo_item, interval=0.03)
        _sleep(0.3)
        pyautogui.press("enter")
        _sleep(0.7)
        pyautogui.press("enter")
        _sleep(2)

        # b. Quantity → Enter
        pyautogui.write(quantidade, interval=0.03)
        _sleep(1)
        pyautogui.press("enter")
        _sleep(3)

        # c. Unit value (2 dp) → Enter → Enter
        pyautogui.write(valor_unitario, interval=0.03)
        _sleep(0.7)
        pyautogui.press("enter")
        _sleep(0.5)
        pyautogui.press("enter")
        _sleep(1)

        # d. CFOP → Enter
        pyautogui.write(cfop, interval=0.03)
        _sleep(0.3)
        pyautogui.press("enter")
        _sleep(1)

        if _checar_erro_popup():
            print(
                f"[OS02] Erro detectado após item {idx + 1} da nota {numero_nota} — abortando."
            )
            return False

    # ------------------------------------------------------------------
    # 11. Save → handle popups → close form
    # ------------------------------------------------------------------
    pyautogui.hotkey("ctrl", "s")

    # Wait up to 12s for any post-save dialog (Advertências or Atenção) before
    # checking for errors — the dialog may take several seconds to appear after
    # AGRO finishes its SEFAZ / internal validation round-trip.
    _deadline = time.time() + 12
    while time.time() < _deadline:
        _titles = [w.title.strip() for w in gw.getAllWindows()]
        if any(t.startswith("[A]dvertência") or t.startswith("[A]dvertencia") for t in _titles):
            break
        if any(t.startswith("Atenção") for t in _titles):
            break
        _sleep(0.5)
    else:
        _sleep(1)

    if _checar_erro_popup():
        print(f"[OS02] Erro crítico ao salvar nota {numero_nota} — abortando.")
        return False

    # Atenção popup → ENTER to confirm
    if wait_window_startswith("Atenção", timeout_seconds=5):
        pyautogui.press("enter")
        _sleep(1)

    if close_form:
        # Switching estab or last note — close the form entirely
        pyautogui.hotkey("ctrl", "f4")
        print(f"[OS02] Nota {numero_nota} salva e fechada.")
    else:
        # Same estab continues — leave form open; caller will press Ctrl+Insert
        print(f"[OS02] Nota {numero_nota} salva (mantendo tela para próxima).")

    _sleep(6)
    return True
