"""Process the second Agro workflow.

Execute the payment authorization flow once after all suppliers from process_1
are completed, repeating the internal flow for each unique EMPRESA.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-06-02
Version: 1.2.2
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import comtypes.client
import pyautogui
import pygetwindow as gw

COMTYPES_CACHE_DIR = Path(os.environ["APPDATA"]) / "comtypes_cache"
COMTYPES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
comtypes.client.gen_dir = str(COMTYPES_CACHE_DIR)

from pywinauto import Application

from robots.robot_OS18.src.replacement_estab import wait_window_startswith

MAIN_WINDOW_TITLE = "FINAGRO-"
AUTHORIZATION_WINDOW_TITLE = "Autorização de Pagamento"
ATTENTION_WINDOW_TITLE = "Atenção"
QUICK_SEARCH_WINDOW_TITLE = "Procura Rápida"

EMPRESA_FIELD_CLASS = "TVsNumRight"
EMPRESA_FIELD_INDEX = 1


def print_open_windows() -> None:
    """Print open windows for debugging."""
    print("\n===== JANELAS ABERTAS =====")

    for window in gw.getAllWindows():
        title = window.title.strip()

        if title:
            print(title)

    print("===== FIM =====\n")


def focus_window(title_start: str, timeout_seconds: int = 10) -> bool:
    """Focus a window by title prefix."""
    start = time.time()

    while time.time() - start < timeout_seconds:
        for window in gw.getAllWindows():
            title = window.title.strip()

            if title.startswith(title_start):
                try:
                    window.activate()
                    time.sleep(1)
                    return True
                except Exception:
                    pass

        time.sleep(0.5)

    print(f"Janela não encontrada: {title_start}")
    print_open_windows()
    return False


def get_today_yyyymmdd_empresa(empresa: str | int) -> str:
    empresa_formatada = str(empresa).strip().zfill(3)
    data_hoje = datetime.now().strftime("%Y%m%d")

    return f"{data_hoje}{empresa_formatada}"


def get_unique_empresas(notas: list[dict[str, Any]]) -> list[str]:
    """Get unique EMPRESA values preserving the original order."""
    empresas: list[str] = []

    for nota in notas:
        empresa = str(nota.get("EMPRESA") or "").strip()

        if empresa and empresa not in empresas:
            empresas.append(empresa)

    return empresas


def get_screen_stable_region() -> tuple[int, int, int, int]:
    """Return the main content region used to detect screen stability."""
    width, height = pyautogui.size()

    return (
        0,
        180,
        width,
        max(100, height - 260),
    )


def wait_screen_stable(
    timeout_seconds: int = 30,
    stable_checks: int = 3,
    interval: float = 0.8,
) -> bool:
    """Wait until the screen content stops changing."""
    print("Aguardando tela estabilizar...")

    start = time.time()
    last_image = None
    stable_count = 0
    region = get_screen_stable_region()

    while time.time() - start < timeout_seconds:
        screenshot = pyautogui.screenshot(region=region)
        current_image = screenshot.tobytes()

        if current_image == last_image:
            stable_count += 1
        else:
            stable_count = 0
            last_image = current_image

        if stable_count >= stable_checks:
            print("Tela estabilizada.")
            return True

        time.sleep(interval)

    print("Tempo limite aguardando a tela estabilizar.")
    return False


def send_ctrl_p_and_wait_reload(step_name: str = "") -> bool:
    """Send CTRL+P and wait for the screen reload to finish."""
    if step_name:
        print(f"Enviando CTRL + P: {step_name}")
    else:
        print("Enviando CTRL + P...")

    pyautogui.hotkey("ctrl", "p")
    time.sleep(1)

    if not wait_screen_stable(timeout_seconds=30):
        print("A tela não estabilizou após CTRL + P.")
        return False

    return True


def close_authorization_payment_screen_if_open() -> None:
    """Close the payment authorization screen if it is open."""
    print("Verificando se a tela Autorização de Pagamento já está aberta...")

    if not focus_window(AUTHORIZATION_WINDOW_TITLE, timeout_seconds=2):
        print("Tela Autorização de Pagamento não estava aberta.")
        return

    print("Fechando tela Autorização de Pagamento para resetar filtros...")

    pyautogui.hotkey("ctrl", "f4")
    time.sleep(1)


def open_authorization_payment_screen() -> bool:
    """Open the payment authorization screen from the main FINAGRO window."""
    print("Abrindo tela Autorização de Pagamento...")

    if not focus_window(MAIN_WINDOW_TITLE, timeout_seconds=10):
        print(f"Tela principal {MAIN_WINDOW_TITLE} não encontrada.")
        return False

    print("Enviando ALT + P...")
    pyautogui.hotkey("alt", "p")
    time.sleep(0.5)

    print("Enviando tecla C...")
    pyautogui.press("c")
    time.sleep(0.5)

    print("Enviando tecla A...")
    pyautogui.press("a")
    time.sleep(1)

    if not wait_window_startswith(AUTHORIZATION_WINDOW_TITLE, timeout_seconds=10):
        print("Tela Autorização de Pagamento não abriu.")
        return False

    print("Tela Autorização de Pagamento encontrada.")
    return True


def prepare_authorization_payment_screen() -> bool:
    """Open a clean payment authorization screen for the current EMPRESA."""
    close_authorization_payment_screen_if_open()

    if not open_authorization_payment_screen():
        return False

    return True


def ensure_authorization_screen() -> bool:
    """Ensure the payment authorization screen is active."""
    if wait_window_startswith(AUTHORIZATION_WINDOW_TITLE, timeout_seconds=2):
        return True

    print("Tela Autorização de Pagamento não está ativa. Tentando focar...")

    if focus_window(AUTHORIZATION_WINDOW_TITLE, timeout_seconds=5):
        return True

    print("Não foi possível focar a tela. Tentando abrir novamente...")
    return open_authorization_payment_screen()


def click_empresa_field_autorizacao() -> bool:
    """Click the EMPRESA field on the payment authorization screen."""
    try:
        app = Application(backend="win32").connect(title_re=".*FINAGRO-.*")

        janela = app.window(title_re=".*Autorização de Pagamento.*")
        janela.wait("visible", timeout=10)
        janela.set_focus()

        campo_empresa = janela.child_window(
            class_name=EMPRESA_FIELD_CLASS,
            found_index=EMPRESA_FIELD_INDEX,
        )

        campo_empresa.click_input()
        time.sleep(0.5)

        return True

    except Exception as error:
        print(f"Erro ao clicar no campo EMPRESA: {error}")
        return False


def fill_empresa_field(empresa: str) -> bool:
    """Fill the EMPRESA field with the provided value."""
    print("Enviando ALT + E...")
    pyautogui.hotkey("alt", "e")
    time.sleep(1)

    if not click_empresa_field_autorizacao():
        print("Não conseguiu clicar no campo EMPRESA.")
        return False

    print("Limpando campo EMPRESA...")
    pyautogui.press("end")
    time.sleep(0.2)

    pyautogui.press("backspace", presses=20, interval=0.02)
    time.sleep(0.3)

    print(f"Digitando EMPRESA: {empresa}")
    pyautogui.write(empresa, interval=0.03)
    time.sleep(1)

    return True


def handle_success_attention_after_save() -> bool:
    """Handle the success attention popup after saving authorization."""
    print("Verificando popup Atenção após CTRL + S...")

    if not wait_window_startswith(ATTENTION_WINDOW_TITLE, timeout_seconds=5):
        print("Popup Atenção não apareceu após salvar.")
        return False

    print("Popup Atenção detectado.")
    print("Duplicatas gravadas com sucesso. Confirmando OK...")

    pyautogui.press("enter")
    time.sleep(1)

    return True


def handle_quick_search_after_date() -> None:
    """Handle Procura Rápida after typing the date if it appears."""
    print("Verificando tela Procura Rápida após informar data...")

    if not wait_window_startswith(QUICK_SEARCH_WINDOW_TITLE, timeout_seconds=3):
        print("Tela Procura Rápida não apareceu.")
        return

    print("Tela Procura Rápida encontrada. Confirmando ENTER 2x...")

    pyautogui.press("enter")
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(0.5)


def run_empresa_authorization_flow(empresa: str) -> bool:
    """Run the authorization flow for one EMPRESA."""
    data_hoje = get_today_yyyymmdd_empresa(empresa)

    if not prepare_authorization_payment_screen():
        print("Não foi possível preparar a tela Autorização de Pagamento.")
        return False

    if not ensure_authorization_screen():
        return False

    print("\n==============================")
    print(f"Processando EMPRESA: {empresa}")
    print(f"Data/empresa usada no process_2: {data_hoje}")
    print("==============================")

    if not fill_empresa_field(empresa):
        return False

    print("Enviando ALT + P...")
    pyautogui.hotkey("alt", "p")
    time.sleep(1)

    print("Enviando ALT + V...")
    pyautogui.hotkey("alt", "v")
    time.sleep(1)

    print("Pressionando SPACE 2x...")
    pyautogui.press("space", presses=2, interval=0.3)
    time.sleep(0.5)

    if not send_ctrl_p_and_wait_reload("após selecionar filtros"):
        return False

    print("Enviando ALT + F...")
    pyautogui.hotkey("alt", "f")
    time.sleep(1)

    print(f"Digitando data: {data_hoje}")
    pyautogui.write(data_hoje, interval=0.03)
    time.sleep(1)

    print("Enviando ENTER após digitar data...")
    pyautogui.press("enter")
    time.sleep(0.5)

    handle_quick_search_after_date()

    if not send_ctrl_p_and_wait_reload("após informar data"):
        return False

    print("Enviando CTRL + S para salvar...")
    pyautogui.hotkey("ctrl", "s")
    time.sleep(2)

    if handle_success_attention_after_save():
        print(f"EMPRESA {empresa} salva com sucesso no process_2.")
    else:
        print(
            "Atenção de sucesso não apareceu após salvar. "
            "Seguindo para a próxima EMPRESA mesmo assim."
        )

    print(f"EMPRESA {empresa} processada com sucesso no process_2.")
    return True


def process_2(notas: list[dict[str, Any]]) -> bool:
    """Process the second workflow once, looping through each unique EMPRESA."""
    print("Iniciando process_2...")

    empresas = get_unique_empresas(notas)

    print(f"Empresas encontradas: {empresas}")

    if not empresas:
        print("Nenhuma EMPRESA encontrada para o process_2.")
        return False

    for empresa in empresas:
        try:
            processed = run_empresa_authorization_flow(empresa)

            if not processed:
                print(f"Falha ao processar EMPRESA {empresa} no process_2.")
                return False

        except Exception as error:
            print(f"Erro ao processar EMPRESA {empresa} no process_2: {error}")
            return False

    close_authorization_payment_screen_if_open()

    print("process_2 finalizado.")
    return True
