"""Process the default Agro workflow.

Execute the financial process by grouping the payment screen by establishment
and then processing account adjustments individually by supplier.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-06-15
Version: 1.6.1
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import pyautogui
import pygetwindow as gw
import pyperclip

from robots.robot_OS18.src.database import buscar_estab_logado, get_connection
from robots.robot_OS18.src.email_alerts import notify_error_before_close
from robots.robot_OS18.src.replacement_estab import switch_establishment, wait_window_startswith

MAIN_WINDOW_TITLE = "FINAGRO-"
PAYMENT_SCREEN_TITLE = "Pagamentos/Exclusões de Títulos e Contas"
ERROR_WINDOW_TITLE = "Erro"
AT_END_OF_TABLE_WINDOW_TITLE = "Erro: %s"
ATTENTION_WINDOW_TITLE = "Atenção"
CONCEITO_WINDOW_TITLE = "Conceito"
ACCOUNT_ADJUSTMENT_TITLE = "Acerto Individual de Conta Movimento"
DUPLICATES_PAYMENT_TITLE = "Pagamento com Duplicatas"
ACCOUNT_MOVEMENT_TITLE = "Conta Movimento - Lançamento"
RECEIPT_WINDOW_TITLE = "Recibo"
PAYMENT_FAILURE_WINDOW_TITLE = "Não foi possível fazer a Baixa"
CONCEITO_BLOCKED_WINDOW_TITLE = "Conceito - Emissão bloqueada!"
FILTER_INVOICE_WINDOW_TITLE = "Filtro de Faturas"

TEST_FATURA_FIXA = ""

ACERTO_FORNECEDOR_FIELD_CLASS = "TVsNumRight"
ACERTO_FORNECEDOR_FIELD_INDEX = 12
PAYMENT_ESTAB_FIELD_CLASS = "TVsNumRight"
PAYMENT_ESTAB_FIELD_INDEX = 4

INTERNAL_WINDOW_TITLES = [
    PAYMENT_SCREEN_TITLE,
    ACCOUNT_ADJUSTMENT_TITLE,
    DUPLICATES_PAYMENT_TITLE,
    ACCOUNT_MOVEMENT_TITLE,
    RECEIPT_WINDOW_TITLE,
    PAYMENT_FAILURE_WINDOW_TITLE,
    "Pagamentos",
    "Exclusões",
    "Títulos",
    "Contas",
    "Acerto Individual",
    "Pagamento com Duplicatas",
    "Conta Movimento",
    "Recibo",
]


def close_attention_after_payment_failure_if_open(
    timeout_seconds: int = 5,
) -> bool:
    print("Verificando Atenção após falhas de baixa...")

    start = time.time()

    while time.time() - start < timeout_seconds:
        attention_window = find_window_by_prefix(ATTENTION_WINDOW_TITLE)

        if not attention_window:
            time.sleep(0.5)
            continue

        print(
            "Tela Atenção encontrada após falhas de baixa. " "Confirmando com ENTER..."
        )

        try:
            attention_window.activate()
            time.sleep(0.5)

            pyautogui.press("enter")
            time.sleep(1)

            return True

        except Exception as error:
            print(f"Erro ao fechar Atenção após falhas de baixa: {error}")
            return False

    print("Nenhuma tela Atenção apareceu após falhas de baixa.")
    return False


def close_no_marked_payment_error_if_open(
    timeout_seconds: int = 5,
) -> bool:
    print(
        "Verificando erro de nenhum título marcado " "ou valor de pagamento zerado..."
    )

    start = time.time()

    while time.time() - start < timeout_seconds:
        error_window = find_window_by_prefix(ERROR_WINDOW_TITLE)

        if not error_window:
            time.sleep(0.5)
            continue

        print("Janela Erro encontrada após salvamento. " "Confirmando com ENTER...")

        try:
            error_window.activate()
            time.sleep(0.5)

            pyautogui.press("enter")
            time.sleep(1)

            return True

        except Exception as error:
            print(
                "Erro ao fechar janela de nenhum título marcado "
                f"ou valor zerado: {error}"
            )
            return False

    print(
        "Erro de nenhum título marcado ou valor zerado " "não apareceu após salvamento."
    )

    return False


def close_optional_receipt_windows(
    timeout_seconds: int = 5,
    max_attempts: int = 5,
) -> int:
    print("Verificando se a tela Recibo apareceu...")

    total_closed = 0
    start = time.time()

    while time.time() - start < timeout_seconds:
        receipt_window = find_window_by_prefix(RECEIPT_WINDOW_TITLE)

        if not receipt_window:
            time.sleep(0.5)
            continue

        break

    for attempt in range(1, max_attempts + 1):
        receipt_window = find_window_by_prefix(RECEIPT_WINDOW_TITLE)

        if not receipt_window:
            break

        total_closed += 1

        print("Tela Recibo encontrada. " f"Fechando ({attempt}/{max_attempts})...")

        try:
            receipt_window.activate()
            time.sleep(0.5)

            pyautogui.hotkey("alt", "f4")
            time.sleep(1)

        except Exception as error:
            print(f"Erro ao fechar tela Recibo: {error}")
            break

    if total_closed:
        print(f"Tela(s) Recibo fechada(s): {total_closed}.")
    else:
        print("Tela Recibo não apareceu. Seguindo sem Recibo.")

    return total_closed


def click_payment_estab_field() -> bool:
    try:
        import os
        from pathlib import Path

        import comtypes.client

        cache_dir = Path(os.environ["APPDATA"]) / "comtypes_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        comtypes.client.gen_dir = str(cache_dir)

        from pywinauto import Application

        app = Application(backend="win32").connect(
            title_re=f".*{PAYMENT_SCREEN_TITLE}.*"
        )

        janela = app.window(title_re=f".*{PAYMENT_SCREEN_TITLE}.*")
        janela.wait("visible", timeout=10)
        janela.set_focus()
        time.sleep(0.5)

        fields = [
            control
            for control in janela.descendants()
            if control.class_name() == PAYMENT_ESTAB_FIELD_CLASS
        ]

        print(
            "Campos encontrados na tela de pagamentos "
            f"com classe {PAYMENT_ESTAB_FIELD_CLASS}: {len(fields)}"
        )

        if PAYMENT_ESTAB_FIELD_INDEX >= len(fields):
            print(
                f"Índice inválido: {PAYMENT_ESTAB_FIELD_INDEX}. "
                f"Campos encontrados: {len(fields)}"
            )
            return False

        campo_estab = fields[PAYMENT_ESTAB_FIELD_INDEX]
        campo_estab.click_input()
        time.sleep(0.5)

        return True

    except Exception as error:
        print(f"Erro ao clicar no campo ESTAB da tela de pagamentos: {error}")
        return False


def print_open_windows() -> None:
    print("\n===== JANELAS ABERTAS =====")

    for window in gw.getAllWindows():
        title = window.title.strip()

        if title:
            print(title)

    print("===== FIM =====\n")


def focus_window(title_start: str, timeout_seconds: int = 10) -> bool:
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


def find_window_by_prefix(title_start: str):
    for window in gw.getAllWindows():
        title = window.title.strip()

        if title.startswith(title_start):
            return window

    return None


def handle_filter_success_popup(timeout_seconds: int = 60) -> bool:
    print("Aguardando janela 'Filtro de Faturas'...")

    start = time.time()

    while time.time() - start < timeout_seconds:
        window = find_window_by_prefix(FILTER_INVOICE_WINDOW_TITLE)

        if window:
            print("Janela 'Filtro de Faturas' encontrada.")
            print("Confirmando mensagem 'Filtrado com Sucesso' com ENTER...")

            try:
                window.activate()
                time.sleep(0.5)

                pyautogui.press("enter")
                time.sleep(1)

                return True

            except Exception as error:
                print(f"Erro ao confirmar janela 'Filtro de Faturas': {error}")
                return False

        time.sleep(0.3)

    print("Janela 'Filtro de Faturas' não apareceu dentro do tempo esperado.")
    print_open_windows()

    return False


def normalize_notas(
    notas: list[dict[str, Any]] | dict[str, Any],
) -> list[dict[str, Any]]:
    if isinstance(notas, dict):
        return [notas]

    return notas


def get_unique_empresas(notas: list[dict[str, Any]]) -> list[str]:
    empresas: list[str] = []

    for nota in notas:
        empresa = str(nota.get("EMPRESA") or "").strip()

        if empresa and empresa not in empresas:
            empresas.append(empresa)

    return empresas


def get_unique_supplier_notes(notas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chaves: set[tuple[str, str]] = set()
    notas_unicas: list[dict[str, Any]] = []

    for nota in notas:
        fornecedor = str(nota.get("FORNECEDOR") or "").strip()
        empresa = str(nota.get("EMPRESA") or "").strip()

        if not fornecedor or not empresa:
            continue

        chave = (fornecedor, empresa)

        if chave in chaves:
            continue

        chaves.add(chave)
        notas_unicas.append(nota)

    return notas_unicas


def get_today_yyyymmdd_empresa(empresa: str | int) -> str:
    if TEST_FATURA_FIXA:
        return TEST_FATURA_FIXA

    empresa_formatada = str(empresa).strip().zfill(3)
    data_hoje = datetime.now().strftime("%Y%m%d")

    return f"{data_hoje}{empresa_formatada}"


def notify_screen_not_opened(
    screen_name: str,
    fornecedor: str = "",
    empresa: str = "",
) -> None:
    notify_error_before_close(
        error_name="Tela não abriu",
        error_description=f"A tela esperada não abriu: {screen_name}.",
        fornecedor=fornecedor,
        empresa=empresa,
    )


def notify_processing_failure(
    error_name: str,
    error_description: str,
    fornecedor: str = "",
    empresa: str = "",
) -> None:
    notify_error_before_close(
        error_name=error_name,
        error_description=error_description,
        fornecedor=fornecedor,
        empresa=empresa,
    )


def close_popup_if_open(title_start: str) -> bool:
    for window in gw.getAllWindows():
        title = window.title.strip()

        if not title.startswith(title_start):
            continue

        print(f"Fechando popup aberto: {title}")

        try:
            window.activate()
            time.sleep(0.5)

            pyautogui.press("enter")
            time.sleep(1)

            return True

        except Exception as error:
            print(f"Erro ao fechar popup '{title}': {error}")

    return False


def close_at_end_of_table_error_if_open(timeout_seconds: int = 5) -> bool:
    print("Verificando popup 'Erro: %s / At end of table'...")

    start = time.time()

    while time.time() - start < timeout_seconds:
        window = find_window_by_prefix(AT_END_OF_TABLE_WINDOW_TITLE)

        if window:
            print("Popup 'Erro: %s' encontrado. Confirmando com ENTER...")

            try:
                window.activate()
                time.sleep(0.5)

                pyautogui.press("enter")
                time.sleep(1)

                return True

            except Exception as error:
                print(f"Erro ao fechar popup 'Erro: %s': {error}")
                return False

        time.sleep(0.5)

    print("Popup 'Erro: %s / At end of table' não apareceu.")
    return False


def close_known_internal_window_if_open() -> bool:
    for window in gw.getAllWindows():
        title = window.title.strip()

        if not title:
            continue

        if title.startswith(MAIN_WINDOW_TITLE):
            continue

        if any(internal_title in title for internal_title in INTERNAL_WINDOW_TITLES):
            print(f"Fechando janela interna aberta: {title}")

            try:
                window.activate()
                time.sleep(0.5)

                pyautogui.hotkey("ctrl", "f4")
                time.sleep(1)

                return True

            except Exception as error:
                print(f"Erro ao fechar janela interna '{title}': {error}")

    return False


def close_payment_screen_if_open() -> None:
    print("Verificando se a tela de pagamentos já está aberta...")

    window = find_window_by_prefix(PAYMENT_SCREEN_TITLE)

    if not window:
        print("Tela de pagamentos não estava aberta.")
        return

    print("Tela de pagamentos já aberta. Fechando...")

    try:
        window.activate()
        time.sleep(0.5)

        pyautogui.hotkey("ctrl", "f4")
        time.sleep(1)

    except Exception as error:
        print(f"Erro ao fechar tela de pagamentos: {error}")


def open_payment_screen() -> bool:
    print("Abrindo tela de pagamentos...")

    if not focus_window(MAIN_WINDOW_TITLE, timeout_seconds=10):
        print(f"Tela principal {MAIN_WINDOW_TITLE} não encontrada.")
        return False

    pyautogui.hotkey("ctrl", "p")
    time.sleep(1)

    if wait_window_startswith(PAYMENT_SCREEN_TITLE, timeout_seconds=5):
        print("Tela Pagamentos/Exclusões de Títulos e Contas aberta.")
        return True

    print("Tela Pagamentos/Exclusões de Títulos e Contas não abriu.")
    return False


def prepare_payment_screen() -> bool:
    close_payment_screen_if_open()

    if not open_payment_screen():
        return False

    return True


def select_payment_estab_filter(
    empresa: str,
    fornecedor: str = "",
) -> bool:
    empresa_formatada = str(empresa).strip()

    if not empresa_formatada:
        notify_processing_failure(
            error_name="ESTAB não informado",
            error_description=(
                "Não foi possível selecionar o estabelecimento na tela de "
                "pagamentos porque a EMPRESA veio vazia."
            ),
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    print(f"Selecionando ESTAB {empresa_formatada} na tela de pagamentos...")

    if not focus_window(PAYMENT_SCREEN_TITLE, timeout_seconds=5):
        notify_screen_not_opened(
            screen_name=PAYMENT_SCREEN_TITLE,
            fornecedor=fornecedor,
            empresa=empresa_formatada,
        )
        return False

    print("Enviando ALT + 2 para aba Estabelecimentos / Filtros Adicionais...")
    pyautogui.hotkey("alt", "2")
    time.sleep(1)

    print("Clicando no campo ESTAB via pywinauto...")

    if not click_payment_estab_field():
        notify_processing_failure(
            error_name="Falha ao clicar no campo ESTAB",
            error_description=(
                "Não foi possível clicar no campo ESTAB "
                "[CLASS:TVsNumRight; INSTANCE:5] da tela de pagamentos."
            ),
            fornecedor=fornecedor,
            empresa=empresa_formatada,
        )
        return False

    print("Limpando campo de ESTAB...")
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)

    pyautogui.press("backspace")
    time.sleep(0.2)

    pyautogui.press("end")
    time.sleep(0.2)

    pyautogui.press("backspace", presses=20, interval=0.02)
    time.sleep(0.3)

    print(f"Digitando ESTAB: {empresa_formatada}")
    pyperclip.copy(empresa_formatada)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)

    print("Enviando ALT + 1 para voltar à aba Principal...")
    pyautogui.hotkey("alt", "1")
    time.sleep(1)

    return True


def ensure_payment_screen_ready(
    fornecedor: str = "",
    empresa: str = "",
) -> bool:
    if wait_window_startswith(PAYMENT_SCREEN_TITLE, timeout_seconds=2):
        return True

    if focus_window(PAYMENT_SCREEN_TITLE, timeout_seconds=3):
        return True

    print("Tela de pagamentos não está ativa. Tentando abrir novamente...")

    if not prepare_payment_screen():
        notify_screen_not_opened(
            screen_name=PAYMENT_SCREEN_TITLE,
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    return True


def fill_fatura_filter(_data_fatura: str) -> None:
    print("Selecionando filtro por vencimento...")

    print("Enviando ALT + V...")
    pyautogui.hotkey("alt", "v")
    time.sleep(1)

    print("Marcando primeira opção com ESPAÇO...")
    pyautogui.press("space")
    time.sleep(0.5)

    print("Enviando TAB...")
    pyautogui.press("tab")
    time.sleep(0.5)

    print("Marcando segunda opção com ESPAÇO...")
    pyautogui.press("space")
    time.sleep(0.5)


def get_screen_stable_region() -> tuple[int, int, int, int]:
    width, height = pyautogui.size()

    return (
        0,
        180,
        width,
        max(100, height - 260),
    )


def handle_post_alt_a_popups_until_finished(
    timeout_seconds: int = 300,
    quiet_seconds: int = 60,
    stable_checks: int = 60,
    interval: float = 0.5,
    fornecedor: str = "",
    empresa: str = "",
) -> bool:
    print("Aguardando finalização do flag das linhas após ALT + A...")

    start = time.time()
    last_popup_time = time.time()
    last_image = None
    stable_count = 0
    region = get_screen_stable_region()

    conceito_blocked_count = 0
    conceito_count = 0
    attention_count = 0

    while time.time() - start < timeout_seconds:
        conceito_blocked_window = find_window_by_prefix(CONCEITO_BLOCKED_WINDOW_TITLE)

        if conceito_blocked_window:
            conceito_blocked_count += 1

            print(
                "Popup Conceito - Emissão bloqueada detectado "
                f"({conceito_blocked_count}). Confirmando com ENTER..."
            )

            try:
                conceito_blocked_window.activate()
                time.sleep(0.4)

                pyautogui.press("enter")
                time.sleep(0.8)

                last_popup_time = time.time()
                stable_count = 0
                last_image = None
                continue

            except Exception as error:
                print(
                    "Erro ao confirmar popup Conceito - Emissão bloqueada: " f"{error}"
                )
                return False

        conceito_window = find_window_by_prefix(CONCEITO_WINDOW_TITLE)

        if conceito_window:
            conceito_count += 1

            print(
                "Popup Conceito detectado "
                f"({conceito_count}). Confirmando com ENTER..."
            )

            try:
                conceito_window.activate()
                time.sleep(0.4)

                pyautogui.press("enter")
                time.sleep(0.8)

                last_popup_time = time.time()
                stable_count = 0
                last_image = None
                continue

            except Exception as error:
                print(f"Erro ao confirmar popup Conceito: {error}")
                return False

        attention_window = find_window_by_prefix(ATTENTION_WINDOW_TITLE)

        if attention_window:
            attention_count += 1

            print(
                "Popup Atenção após ALT + A detectado "
                f"({attention_count}). Confirmando com ENTER..."
            )

            try:
                attention_window.activate()
                time.sleep(0.4)

                pyautogui.press("enter")
                time.sleep(0.8)

                last_popup_time = time.time()
                stable_count = 0
                last_image = None
                continue

            except Exception as error:
                print(f"Erro ao confirmar popup Atenção após ALT + A: {error}")
                return False

        try:
            screenshot = pyautogui.screenshot(region=region)
            current_image = screenshot.tobytes()

            if current_image == last_image:
                stable_count += 1
            else:
                stable_count = 0
                last_image = current_image

        except Exception as error:
            print(f"Erro ao capturar tela para validar estabilidade: {error}")
            stable_count = 0
            last_image = None

        without_popup_seconds = time.time() - last_popup_time

        if without_popup_seconds >= quiet_seconds and stable_count >= stable_checks:
            print(
                "Nenhum popup pós-ALT+A apareceu nos últimos "
                f"{quiet_seconds} segundos."
            )
            print(
                "Tela considerada estável. Flag das linhas finalizado. "
                f"Conceitos bloqueados confirmados: {conceito_blocked_count}. "
                f"Conceitos confirmados: {conceito_count}. "
                f"Atenções confirmadas: {attention_count}."
            )
            return True

        time.sleep(interval)

    notify_processing_failure(
        error_name="Tempo limite após ALT+A",
        error_description=(
            "O processo ficou aguardando a finalização do flag das linhas após "
            "ALT + A, mas o tempo limite foi atingido. "
            f"Conceitos bloqueados confirmados: {conceito_blocked_count}. "
            f"Conceitos confirmados: {conceito_count}. "
            f"Atenções confirmadas: {attention_count}."
        ),
        fornecedor=fornecedor,
        empresa=empresa,
    )

    print_open_windows()
    return False


def wait_blocking_popup_during_reload() -> bool:
    popup_titles = [
        ERROR_WINDOW_TITLE,
        ATTENTION_WINDOW_TITLE,
        CONCEITO_WINDOW_TITLE,
        PAYMENT_FAILURE_WINDOW_TITLE,
    ]

    for popup_title in popup_titles:
        if wait_window_startswith(popup_title, timeout_seconds=1):
            print(
                "Popup detectado durante carregamento: "
                f"{popup_title}. Interrompendo espera de estabilização."
            )
            return True

    return False


def wait_screen_stable(
    timeout_seconds: int = 30,
    stable_checks: int = 3,
    interval: float = 0.8,
) -> bool:
    print("Aguardando tela estabilizar...")

    start = time.time()
    last_image = None
    stable_count = 0
    region = get_screen_stable_region()

    while time.time() - start < timeout_seconds:
        if wait_blocking_popup_during_reload():
            return True

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

    if wait_blocking_popup_during_reload():
        return True

    print("Tempo limite aguardando a tela estabilizar.")
    return False


def send_ctrl_p_and_wait_reload(step_name: str = "") -> bool:
    if step_name:
        print(f"Enviando CTRL + P: {step_name}")
    else:
        print("Enviando CTRL + P...")

    pyautogui.hotkey("ctrl", "p")
    time.sleep(1)

    if wait_blocking_popup_during_reload():
        return True

    if not wait_screen_stable(timeout_seconds=30):
        print("A tela não estabilizou após CTRL + P.")
        return False

    return True


def handle_conceito_after_filter(
    fornecedor: str = "",
    empresa: str = "",
) -> bool:
    print("Verificando popup Conceito após filtro...")

    if not wait_window_startswith(CONCEITO_WINDOW_TITLE, timeout_seconds=3):
        print("Popup Conceito não apareceu.")
        return False

    notify_error_before_close(
        error_name="Conceito",
        error_description="Popup Conceito exibido após o filtro de vencimento.",
        fornecedor=fornecedor,
        empresa=empresa,
    )

    print("Popup Conceito detectado. Confirmando OK e seguindo próximo ESTAB...")

    pyautogui.press("enter")
    time.sleep(1)

    return True


def handle_no_pending_title(
    fornecedor: str = "",
    empresa: str = "",
) -> bool:
    print("Verificando janela Erro...")

    if not wait_window_startswith(ERROR_WINDOW_TITLE, timeout_seconds=3):
        print("Janela Erro não apareceu.")
        return False

    print("Janela Erro detectada: Nenhum Título Pendente foi Encontrado.")
    print("Confirmando OK e seguindo para o próximo ESTAB sem notificar erro...")

    pyautogui.press("enter")
    time.sleep(1)

    return True


def handle_no_launch_found_attention(
    fornecedor: str = "",
    empresa: str = "",
    notify: bool = True,
) -> bool:
    print("Verificando popup Atenção: Nenhum lançamento foi encontrado...")

    if not wait_window_startswith(ATTENTION_WINDOW_TITLE, timeout_seconds=4):
        print("Popup Atenção não apareceu.")
        return False

    if notify:
        notify_error_before_close(
            error_name="Nenhum Lançamento Encontrado",
            error_description="Nenhum lançamento foi encontrado.",
            fornecedor=fornecedor,
            empresa=empresa,
        )

    print("Popup Atenção detectado.")
    print("Nenhum lançamento foi encontrado. Confirmando OK...")

    pyautogui.press("enter")
    time.sleep(1)

    return True


def click_fornecedor_field_acerto() -> bool:
    try:
        import os
        from pathlib import Path

        import comtypes.client

        cache_dir = Path(os.environ["APPDATA"]) / "comtypes_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        comtypes.client.gen_dir = str(cache_dir)

        from pywinauto import Application

        app = Application(backend="win32").connect(
            title_re=f".*{ACCOUNT_ADJUSTMENT_TITLE}.*"
        )

        janela = app.window(title_re=f".*{ACCOUNT_ADJUSTMENT_TITLE}.*")
        janela.wait("visible", timeout=10)
        janela.set_focus()
        time.sleep(0.5)

        fields = [
            control
            for control in janela.descendants()
            if control.class_name() == ACERTO_FORNECEDOR_FIELD_CLASS
        ]

        print(
            "Campos encontrados no Acerto Individual "
            f"com classe {ACERTO_FORNECEDOR_FIELD_CLASS}: {len(fields)}"
        )

        if ACERTO_FORNECEDOR_FIELD_INDEX >= len(fields):
            print(
                f"Índice inválido: {ACERTO_FORNECEDOR_FIELD_INDEX}. "
                f"Campos encontrados: {len(fields)}"
            )
            return False

        campo_fornecedor = fields[ACERTO_FORNECEDOR_FIELD_INDEX]
        campo_fornecedor.click_input()
        time.sleep(0.5)

        return True

    except Exception as error:
        print(f"Erro ao clicar no campo FORNECEDOR do Acerto Individual: {error}")
        return False


def fill_fornecedor_acerto_field(fornecedor: str) -> bool:
    if not click_fornecedor_field_acerto():
        print("Não conseguiu clicar no campo FORNECEDOR do Acerto Individual.")
        return False

    print("Limpando campo FORNECEDOR do Acerto Individual...")

    pyautogui.press("end")
    time.sleep(0.2)

    pyautogui.press("backspace", presses=30, interval=0.02)
    time.sleep(0.3)

    print(f"Enviando fornecedor no acerto: {fornecedor}")
    pyautogui.write(fornecedor, interval=0.03)
    time.sleep(1)

    return True


def close_payment_failure_popups_until_finished(
    max_attempts: int = 200,
) -> int:
    print("Verificando tela 'Não foi possível fazer a Baixa'...")

    total_closed = 0

    for attempt in range(1, max_attempts + 1):
        if wait_window_startswith(PAYMENT_FAILURE_WINDOW_TITLE, timeout_seconds=3):
            total_closed += 1

            print(
                "Tela 'Não foi possível fazer a Baixa' encontrada. "
                f"Confirmando com ENTER ({attempt}/{max_attempts})..."
            )

            pyautogui.press("enter")
            time.sleep(1)
            continue

        print("Tela 'Não foi possível fazer a Baixa' não apareceu mais.")
        break

    if total_closed:
        print(
            "Tela(s) 'Não foi possível fazer a Baixa' fechada(s): " f"{total_closed}."
        )

    return total_closed


def save_account_movement_until_receipt(
    max_attempts: int = 200,
    fornecedor: str = "",
    empresa: str = "",
) -> bool:
    print("Verificando tela Conta Movimento - Lançamento...")

    for attempt in range(1, max_attempts + 1):
        if wait_window_startswith(ACCOUNT_MOVEMENT_TITLE, timeout_seconds=3):
            print(
                "Tela Conta Movimento - Lançamento encontrada. "
                f"Enviando CTRL + S ({attempt}/{max_attempts})..."
            )

            pyautogui.hotkey("ctrl", "s")
            time.sleep(1)
            continue

        print("Tela Conta Movimento - Lançamento não apareceu mais.")
        break

    close_payment_failure_popups_until_finished(max_attempts=max_attempts)
    close_attention_after_payment_failure_if_open(timeout_seconds=5)
    close_no_marked_payment_error_if_open(timeout_seconds=5)
    close_at_end_of_table_error_if_open(timeout_seconds=5)

    close_optional_receipt_windows(
        timeout_seconds=5,
        max_attempts=50,
    )

    print("Recibo tratado como opcional. " "Seguindo fluxo após salvamento.")

    return True


def close_post_receipt_filter_popups(
    fornecedor: str = "",
    empresa: str = "",
    timeout_seconds: int = 90,
) -> None:
    print("Verificando popups após salvamento...")

    close_at_end_of_table_error_if_open(timeout_seconds=5)

    start = time.time()
    filter_closed = False

    while time.time() - start < timeout_seconds:
        close_at_end_of_table_error_if_open(timeout_seconds=1)

        window = find_window_by_prefix(FILTER_INVOICE_WINDOW_TITLE)

        if window:
            filter_closed = True

            print("Filtro de Faturas pós-salvamento encontrado.")
            print("Confirmando com ENTER...")

            try:
                window.activate()
                time.sleep(0.5)

                pyautogui.press("enter")
                time.sleep(1)

            except Exception as error:
                print(f"Erro ao fechar Filtro de Faturas pós-salvamento: {error}")

            break

        time.sleep(0.5)

    if filter_closed:
        print("Filtro de Faturas pós-salvamento fechado.")

        close_at_end_of_table_error_if_open(timeout_seconds=5)

        if wait_window_startswith(ERROR_WINDOW_TITLE, timeout_seconds=3):
            print("Janela Erro pós-salvamento detectada.")
            print("Confirmando com ENTER sem notificar erro...")

            pyautogui.press("enter")
            time.sleep(1)

        return

    print("Nenhum popup de Filtro de Faturas apareceu após o salvamento.")


def close_until_main_finagro(max_attempts: int = 25) -> bool:
    print(f"Fechando telas até voltar para {MAIN_WINDOW_TITLE}...")

    for attempt in range(1, max_attempts + 1):
        print(f"Tentativa {attempt}/{max_attempts}")

        if close_popup_if_open(ATTENTION_WINDOW_TITLE):
            continue

        if close_popup_if_open(ERROR_WINDOW_TITLE):
            continue

        if close_popup_if_open(CONCEITO_WINDOW_TITLE):
            continue

        if close_popup_if_open(FILTER_INVOICE_WINDOW_TITLE):
            continue

        if close_popup_if_open(PAYMENT_FAILURE_WINDOW_TITLE):
            continue

        if close_known_internal_window_if_open():
            continue

        if focus_window(MAIN_WINDOW_TITLE, timeout_seconds=3):
            print(
                f"Tela principal {MAIN_WINDOW_TITLE} ativa "
                "e sem janelas internas conhecidas."
            )
            return True

        print("Tela principal ainda não ficou ativa. Enviando ESC...")
        pyautogui.press("esc")
        time.sleep(1)

    print(f"Não foi possível retornar para {MAIN_WINDOW_TITLE}.")
    print_open_windows()

    return False


def ensure_estab_for_account_adjustment(
    empresa: str,
    fornecedor: str = "",
) -> bool:
    print("Preparando troca de ESTAB antes do Acerto Individual...")

    if not close_until_main_finagro():
        notify_processing_failure(
            error_name="Falha ao retornar tela principal",
            error_description=(
                f"Não foi possível retornar para {MAIN_WINDOW_TITLE} "
                "antes de trocar o estabelecimento para o Acerto Individual."
            ),
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    try:
        estab_nota = int(str(empresa).strip())
    except ValueError:
        notify_processing_failure(
            error_name="ESTAB inválido",
            error_description=f"EMPRESA/ESTAB inválido recebido na consulta: {empresa}.",
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    try:
        with get_connection() as connection:
            estab_logado = int(buscar_estab_logado(connection))

    except Exception as error:
        notify_processing_failure(
            error_name="Falha ao consultar ESTAB logado",
            error_description=f"Não foi possível consultar o ESTAB logado: {error}",
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    print(f"ESTAB logado: {estab_logado}")
    print(f"ESTAB do fornecedor: {estab_nota}")

    if estab_logado == estab_nota:
        print("ESTAB já está correto para o fornecedor.")
        return True

    print(f"Trocando ESTAB para {estab_nota}...")

    if not switch_establishment(estab_nota):
        notify_processing_failure(
            error_name="Falha ao trocar ESTAB",
            error_description=f"Não foi possível trocar para o ESTAB {estab_nota}.",
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    print("Troca de ESTAB realizada com sucesso.")

    if not wait_window_startswith(MAIN_WINDOW_TITLE, timeout_seconds=10):
        notify_processing_failure(
            error_name="Tela principal não retornou após troca de ESTAB",
            error_description=(
                f"A tela {MAIN_WINDOW_TITLE} não ficou ativa após trocar "
                f"para o ESTAB {estab_nota}."
            ),
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    return True


def send_alt_m_v() -> None:
    print("Enviando ALT + M + V...")

    pyautogui.keyDown("alt")
    time.sleep(0.2)

    pyautogui.press("m")
    time.sleep(0.2)

    pyautogui.press("v")
    time.sleep(0.2)

    pyautogui.keyUp("alt")
    time.sleep(1)


def handle_attention_after_account_search(
    fornecedor: str = "",
    empresa: str = "",
) -> bool:
    print("Verificando popup Atenção após CTRL + P no Acerto Individual...")

    if not wait_window_startswith(ATTENTION_WINDOW_TITLE, timeout_seconds=3):
        print("Popup Atenção não apareceu.")
        return False

    notify_error_before_close(
        error_name="Atenção no Acerto Individual",
        error_description="Popup Atenção exibido após CTRL + P no Acerto Individual.",
        fornecedor=fornecedor,
        empresa=empresa,
    )

    print("Popup Atenção detectado após CTRL + P no Acerto Individual.")
    print("Confirmando OK e encerrando fornecedor atual...")

    pyautogui.press("enter")
    time.sleep(1)

    close_until_main_finagro()

    return True


def process_payment_by_empresa(
    empresa: str,
    configurar_filtro_vencimento: bool = True,
) -> bool:
    data_fatura = get_today_yyyymmdd_empresa(empresa)

    print("\n==============================")
    print(f"Processando filtro por vencimento do ESTAB: {empresa}")
    print(f"Referência de data/empresa mantida: {data_fatura}")
    print("==============================")

    if not ensure_payment_screen_ready(empresa=empresa):
        return False

    if configurar_filtro_vencimento:
        fill_fatura_filter(data_fatura)

        print("Enviando CTRL + P para aplicar filtro por vencimento...")
        pyautogui.hotkey("ctrl", "p")
        time.sleep(1)
    else:
        print(
            "Filtro por vencimento já configurado. "
            "Executando novamente com CTRL + P..."
        )
        pyautogui.hotkey("ctrl", "p")
        time.sleep(1)

    if not handle_filter_success_popup():
        notify_processing_failure(
            error_name="Filtro de Faturas não confirmou",
            error_description=(
                "A janela 'Filtro de Faturas' com a mensagem "
                "'Filtrado com Sucesso' não apareceu após executar o filtro."
            ),
            empresa=empresa,
        )
        return False

    if handle_no_pending_title(empresa=empresa):
        print(f"ESTAB {empresa} encerrado porque não possui título pendente.")
        return True

    if close_at_end_of_table_error_if_open(timeout_seconds=2):
        print(f"ESTAB {empresa} encerrado por Erro: %s após filtro.")
        return True

    if handle_conceito_after_filter(empresa=empresa):
        print(f"ESTAB {empresa} encerrado por conceito após filtro de vencimento.")
        return True

    print("Enviando ALT + A...")
    pyautogui.hotkey("alt", "a")
    time.sleep(1)

    if not handle_post_alt_a_popups_until_finished(
        timeout_seconds=300,
        quiet_seconds=10,
        stable_checks=10,
        interval=0.5,
        empresa=empresa,
    ):
        return False

    print("Enviando ALT + P...")
    pyautogui.hotkey("alt", "p")
    time.sleep(1)

    print("Enviando enter e zerando campo dinheiro...")
    pyautogui.press("enter")
    time.sleep(1)

    pyautogui.press("0", presses=10, interval=0.02)
    time.sleep(0.5)

    print("Chegando no campo 3-Cta Mov.")
    pyautogui.press("enter", presses=2, interval=0.5)
    time.sleep(1)

    print("Enviando CTRL + S para salvar...")
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)

    if not save_account_movement_until_receipt(empresa=empresa):
        print(f"Falha ao salvar Conta Movimento no ESTAB {empresa}.")
        return False

    close_post_receipt_filter_popups(
        fornecedor="",
        empresa=empresa,
        timeout_seconds=90,
    )

    print(f"Processo do ESTAB {empresa} finalizado.")
    return True


def process_account_adjustment_by_supplier(nota: dict[str, Any]) -> bool:
    fornecedor = str(nota.get("FORNECEDOR") or "").strip()
    empresa = str(nota.get("EMPRESA") or "").strip()
    data_hoje = get_today_yyyymmdd_empresa(empresa)
    historico = f"RPA-FATURA UNIFICADA {data_hoje}"

    print("\n==============================")
    print(f"Processando Acerto Individual do fornecedor: {fornecedor}")
    print(f"Empresa/Estab: {empresa}")
    print(f"Data/empresa usada no acerto: {data_hoje}")
    print("==============================")

    if not fornecedor:
        notify_processing_failure(
            error_name="Fornecedor não informado",
            error_description="FORNECEDOR não veio preenchido na consulta.",
            fornecedor=fornecedor,
            empresa=empresa,
        )
        print("FORNECEDOR não informado na consulta.")
        return False

    if not ensure_estab_for_account_adjustment(
        empresa=empresa,
        fornecedor=fornecedor,
    ):
        return False

    send_alt_m_v()

    if not wait_window_startswith(ACCOUNT_ADJUSTMENT_TITLE, timeout_seconds=10):
        notify_screen_not_opened(
            screen_name=ACCOUNT_ADJUSTMENT_TITLE,
            fornecedor=fornecedor,
            empresa=empresa,
        )

        print("Tela Acerto Individual de Conta Movimento não abriu.")
        return False

    if not fill_fornecedor_acerto_field(fornecedor):
        notify_processing_failure(
            error_name="Falha ao preencher fornecedor",
            error_description=(
                "Não foi possível clicar, limpar ou preencher o campo fornecedor "
                "na tela Acerto Individual de Conta Movimento."
            ),
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    print("Enviando CTRL + P...")
    pyautogui.hotkey("ctrl", "p")
    time.sleep(1)

    if handle_attention_after_account_search(
        fornecedor=fornecedor,
        empresa=empresa,
    ):
        print("Fornecedor encerrado por Atenção no Acerto Individual.")
        return True

    print("Enviando ALT + M...")
    pyautogui.hotkey("alt", "m")
    time.sleep(1)

    print("Enviando ALT + 3...")
    pyautogui.hotkey("alt", "3")
    time.sleep(1)

    print("Enviando CTRL + ENTER...")
    pyautogui.hotkey("ctrl", "enter")
    time.sleep(1)

    if not wait_window_startswith(DUPLICATES_PAYMENT_TITLE, timeout_seconds=10):
        notify_screen_not_opened(
            screen_name=DUPLICATES_PAYMENT_TITLE,
            fornecedor=fornecedor,
            empresa=empresa,
        )

        print("Tela Pagamento com Duplicatas não abriu.")
        return False

    print("Tela Pagamento com Duplicatas encontrada.")

    print("Enviando TAB 3x...")
    pyautogui.press("tab", presses=3, interval=0.2)
    time.sleep(0.5)

    print("Digitando 2...")
    pyautogui.write("2", interval=0.03)
    time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(0.5)

    print("Digitando 0...")
    pyautogui.write("0", interval=0.03)
    time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(0.5)

    pyautogui.press("tab")
    time.sleep(0.5)

    print(f"Digitando histórico: {historico}")
    pyautogui.write(historico, interval=0.03)
    time.sleep(0.5)

    print("Enviando TAB 10x...")
    pyautogui.press("tab", presses=10, interval=0.15)
    time.sleep(0.5)

    print(f"Digitando primeira data: {data_hoje}")
    pyautogui.write(data_hoje, interval=0.03)
    time.sleep(0.5)

    pyautogui.press("tab")
    time.sleep(0.5)

    print(f"Digitando segunda data: {data_hoje}")
    pyautogui.write(data_hoje, interval=0.03)
    time.sleep(0.5)

    print("Enviando ALT + G...")
    pyautogui.hotkey("alt", "g")
    time.sleep(1.5)

    print("Enviando CTRL + S 2x...")
    pyautogui.hotkey("ctrl", "s")
    time.sleep(1.5)

    pyautogui.hotkey("ctrl", "s")
    time.sleep(1.5)

    close_payment_failure_popups_until_finished(max_attempts=50)
    close_at_end_of_table_error_if_open(timeout_seconds=5)

    print(
        "Recibo está desabilitado no sistema. "
        "Seguindo fluxo sem aguardar tela Recibo."
    )

    if handle_no_launch_found_attention(
        fornecedor=fornecedor,
        empresa=empresa,
        notify=False,
    ):
        print("Atenção de nenhum lançamento tratada após salvamento.")

    if not close_until_main_finagro():
        notify_processing_failure(
            error_name="Falha ao retornar tela principal",
            error_description=(
                f"Não foi possível retornar para {MAIN_WINDOW_TITLE} "
                "após finalizar o processo no Acerto Individual."
            ),
            fornecedor=fornecedor,
            empresa=empresa,
        )
        return False

    print(f"Acerto Individual do fornecedor {fornecedor} finalizado.")
    return True


def process_1(notas: list[dict[str, Any]] | dict[str, Any]) -> bool:
    print("Iniciando process_1...")

    notas_processamento = normalize_notas(notas)
    empresas = get_unique_empresas(notas_processamento)

    print(f"Total de linhas recebidas: {len(notas_processamento)}")
    print(f"Empresas/Estabs encontrados: {empresas}")

    if not notas_processamento:
        print("Nenhuma linha recebida para o process_1.")
        return False

    if not empresas:
        notify_processing_failure(
            error_name="Empresa não informada",
            error_description="Nenhuma EMPRESA veio preenchida na consulta.",
        )
        print("Nenhuma EMPRESA encontrada na consulta.")
        return False

    primeira_nota = notas_processamento[0]
    primeiro_fornecedor = str(primeira_nota.get("FORNECEDOR") or "").strip()
    primeira_empresa = str(primeira_nota.get("EMPRESA") or "").strip()

    print("\n===== FASE 1: Pagamentos/Exclusões por ESTAB =====")
    print(
        "A tela de pagamentos será aberta uma vez. "
        "Cada ESTAB será selecionado na aba ALT + 2, sem marcar Todos."
    )

    if not prepare_payment_screen():
        notify_screen_not_opened(
            screen_name=PAYMENT_SCREEN_TITLE,
            fornecedor=primeiro_fornecedor,
            empresa=primeira_empresa,
        )
        print("Não foi possível preparar a tela de pagamentos.")
        return False

    for index_empresa, empresa in enumerate(empresas):
        print("\n==============================")
        print(f"Preparando filtro interno para ESTAB: {empresa}")
        print("==============================")

        if not select_payment_estab_filter(
            empresa=empresa,
            fornecedor=primeiro_fornecedor,
        ):
            print(f"Não foi possível selecionar o ESTAB {empresa}.")
            return False

        configurar_filtro_vencimento = index_empresa == 0

        if not process_payment_by_empresa(
            empresa=empresa,
            configurar_filtro_vencimento=configurar_filtro_vencimento,
        ):
            print(f"Falha ao processar pagamento por vencimento no ESTAB {empresa}.")
            return False

    print("Fase 1 finalizada: Pagamentos/Exclusões por ESTAB.")

    if not close_until_main_finagro():
        notify_processing_failure(
            error_name="Falha ao retornar tela principal",
            error_description=(
                f"Não foi possível retornar para {MAIN_WINDOW_TITLE} "
                "após finalizar a fase de pagamentos por ESTAB."
            ),
            fornecedor=primeiro_fornecedor,
            empresa=primeira_empresa,
        )
        return False

    print("\n===== FASE 2: Acerto Individual por FORNECEDOR =====")

    notas_fornecedores_unicos = get_unique_supplier_notes(notas_processamento)

    print(
        "Fornecedores/empresas únicos para etapa 2: "
        f"{len(notas_fornecedores_unicos)}"
    )

    for nota in notas_fornecedores_unicos:
        if not process_account_adjustment_by_supplier(nota):
            fornecedor = str(nota.get("FORNECEDOR") or "").strip()
            empresa = str(nota.get("EMPRESA") or "").strip()

            print(
                "Falha ao processar Acerto Individual "
                f"do fornecedor {fornecedor} / empresa {empresa}."
            )
            return False

    print("process_1 finalizado.")
    return True
