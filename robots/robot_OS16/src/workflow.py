"""Run the OS16 workflow steps.

Update robot execution status, search pending notes, and open Agro when needed.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-12
Version: 1.0.0
"""

from __future__ import annotations

import time

import pyautogui
from pywinauto import Desktop

from config import AGRO_EXE, COMPUTADOR_ROBO
from core.database import (
    buscar_executando,
    buscar_proximo_pendente,
    get_connection,
    marcar_executando,
)
from robots.robot_OS16.src.agro_alerts import (
    confirm_attention_popup,
    confirm_establishment_selection,
)
from robots.robot_OS16.src.agro_app import kill_agro_process, start_agro
from robots.robot_OS16.src.agro_login import login_agro
from robots.robot_OS16.src.database import buscar_notas_pendentes
from robots.robot_OS16.src.replacement_estab import (
    switch_establishment,
    wait_window_startswith,
)

_INTERRUPT_CHECK_INTERVAL = 180  # 3 minutos

_ENVIO_NFE_TITLE = "Envio/Retorno de NFe em Lotes"
_ENVIO_NFE_CLASS = "TFEnvNFeLote"

_ENVIAR_LOTE_NFS_TITLE = "Enviar Lote NFs"
_ENVIAR_LOTE_NFS_CLASS = "#32770"
_ENVIAR_LOTE_NFS_TIMEOUT_SECONDS = 8

_AVISO_TITLE = "Aviso"
_AVISO_CLASS = "TMessageForm"
_AVISO_TIMEOUT_SECONDS = 8

_ATENCAO_TITLE = "Atenção"
_ATENCAO_CLASS = "#32770"
_ATENCAO_NENHUMA_NF_TEXT = "Nenhuma NF foi Selecionada para o Envio"
_ATENCAO_TIMEOUT_SECONDS = 8

_CONFIRM_TITLE = "Confirme"
_CONFIRM_CLASS = "TMessageForm"

_CONFIRM_TIMEOUT_SECONDS = 120


def _esta_interrompido() -> bool:
    """Return True when the robot is no longer EXECUTANDO in U_ROBOT_LOG."""
    with get_connection() as conn:
        return buscar_executando(conn, COMPUTADOR_ROBO) is None


def _reiniciar_agro() -> None:
    """Restart Agro, log in, and confirm initial popups."""
    print("Reiniciando Agro...")

    kill_agro_process("Agro3C.exe")
    start_agro(AGRO_EXE)

    time.sleep(5)

    login_agro()
    print("Login realizado.")

    confirm_attention_popup()
    confirm_establishment_selection()

    if not wait_window_startswith("AGRO-AG", timeout_seconds=15):
        raise RuntimeError("Tela AGRO-AG não abriu após reinício.")

    print("Agro pronto para uso.")


def _abrir_tela_nota_fiscal() -> None:
    """Open the Nota Fiscal screen through the Agro menu."""
    print("Abrindo tela de Nota Fiscal...")

    pyautogui.keyDown("alt")
    time.sleep(0.1)
    pyautogui.press("d")
    time.sleep(0.3)
    pyautogui.keyUp("alt")
    time.sleep(0.2)

    pyautogui.keyDown("alt")
    time.sleep(0.1)
    pyautogui.press("d")
    time.sleep(0.3)
    pyautogui.keyUp("alt")
    time.sleep(0.2)

    pyautogui.press("d")
    time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(0.3)

    pyautogui.press("down", presses=2, interval=0.15)
    time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(0.3)

    pyautogui.press("down")
    time.sleep(0.3)

    pyautogui.press("enter")
    time.sleep(0.5)

    print("Comando para abrir tela de Nota Fiscal enviado.")


def _obter_tela_envio_nfe(timeout_seconds: int = 10):
    """Return the Envio/Retorno de NFe em Lotes window when available."""
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            window = Desktop(backend="win32").window(
                title=_ENVIO_NFE_TITLE,
                class_name=_ENVIO_NFE_CLASS,
            )

            if window.exists(timeout=1):
                window.set_focus()
                return window

        except Exception:
            pass

        time.sleep(0.5)

    return None


def _clicar_botao_envio_nfe(window) -> None:
    """Click the second TButton in the Envio/Retorno de NFe screen."""
    print("Executando Ctrl+P...")

    window.set_focus()
    time.sleep(3)

    pyautogui.hotkey("ctrl", "p")
    time.sleep(3)

    print("Clicando no botão TButton2...")

    button = window.child_window(class_name="TButton", found_index=1)

    if not button.exists(timeout=5):
        raise RuntimeError("Botão TButton2 não encontrado na tela Envio/Retorno.")

    button.wait("visible enabled", timeout=5)
    button.click_input()

    print("Botão TButton2 clicado.")


def _obter_textos_janela(window) -> str:
    """Return visible texts from a window when available."""
    try:
        return "\n".join(text for text in window.texts() if text)
    except Exception:
        return ""


def _clicar_ok_janela_enviar_lote_nfs(window) -> None:
    """Click OK on the Enviar Lote NFs popup."""
    try:
        ok_button = window.child_window(title="OK", class_name="Button")

        if not ok_button.exists(timeout=2):
            ok_button = window.child_window(control_id=2, class_name="Button")

        if not ok_button.exists(timeout=2):
            ok_button = window.child_window(class_name="Button", found_index=0)

        if ok_button.exists(timeout=3):
            ok_button.wait("visible enabled", timeout=3)
            ok_button.click_input()
            return

    except Exception:
        pass

    pyautogui.press("enter")


def _clicar_ok_janela_aviso(window) -> None:
    """Click OK on the Aviso popup."""
    try:
        ok_button = window.child_window(title="&OK", class_name="TButton")

        if not ok_button.exists(timeout=2):
            ok_button = window.child_window(class_name="TButton", found_index=0)

        if ok_button.exists(timeout=3):
            ok_button.wait("visible enabled", timeout=3)
            ok_button.click_input()
            return

    except Exception:
        pass

    pyautogui.press("enter")


def _confirmar_popup_enviar_lote_nfs(
    timeout_seconds: int = _ENVIAR_LOTE_NFS_TIMEOUT_SECONDS,
) -> bool:
    """Confirm the Enviar Lote NFs popup when it appears."""
    print(f"Aguardando tela Enviar Lote NFs por até {timeout_seconds} segundos...")

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            window = Desktop(backend="win32").window(
                title=_ENVIAR_LOTE_NFS_TITLE,
                class_name=_ENVIAR_LOTE_NFS_CLASS,
            )

            if window.exists(timeout=1):
                window.set_focus()
                time.sleep(0.2)

                textos = _obter_textos_janela(window)

                if textos:
                    print("Tela Enviar Lote NFs localizada com texto:")
                    print(textos)
                else:
                    print("Tela Enviar Lote NFs localizada.")

                _clicar_ok_janela_enviar_lote_nfs(window)

                print("Tela Enviar Lote NFs confirmada com OK.")
                return True

        except Exception:
            pass

        time.sleep(0.5)

    print("Tela Enviar Lote NFs não apareceu dentro do tempo limite.")
    return False


def _confirmar_popup_atencao_nenhuma_nf(
    timeout_seconds: int = _ATENCAO_TIMEOUT_SECONDS,
) -> bool:
    """Confirm the Atenção popup when no NF was selected for sending."""
    print(f"Aguardando tela Atenção por até {timeout_seconds} segundos...")

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            window = Desktop(backend="win32").window(
                title=_ATENCAO_TITLE,
                class_name=_ATENCAO_CLASS,
            )

            if window.exists(timeout=1):
                textos = _obter_textos_janela(window)

                if _ATENCAO_NENHUMA_NF_TEXT not in textos:
                    time.sleep(0.5)
                    continue

                window.set_focus()
                time.sleep(0.2)

                print(f"Tela Atenção localizada: {textos.strip()}")

                ok_button = window.child_window(class_name="Button", found_index=0)

                if ok_button.exists(timeout=3):
                    ok_button.wait("visible enabled", timeout=3)
                    ok_button.click_input()
                else:
                    pyautogui.press("enter")

                print("Tela Atenção confirmada com OK. Indo para próxima nota.")
                return True

        except Exception:
            pass

        time.sleep(0.5)

    print("Tela Atenção não apareceu dentro do tempo limite.")
    return False


def _confirmar_popup_aviso_erro(
    timeout_seconds: int = _AVISO_TIMEOUT_SECONDS,
) -> bool:
    """Confirm the Aviso popup and signal that Agro must be restarted."""
    print(f"Aguardando tela Aviso por até {timeout_seconds} segundos...")

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            window = Desktop(backend="win32").window(
                title=_AVISO_TITLE,
                class_name=_AVISO_CLASS,
            )

            if window.exists(timeout=1):
                window.set_focus()
                time.sleep(0.2)

                textos = _obter_textos_janela(window)

                if textos:
                    print("Tela Aviso localizada com texto:")
                    print(textos)
                else:
                    print("Tela Aviso localizada.")

                _clicar_ok_janela_aviso(window)

                print(
                    "Tela Aviso confirmada com OK. "
                    "O Agro será reiniciado e o fluxo seguirá para a próxima nota."
                )
                return True

        except Exception:
            pass

        time.sleep(0.5)

    print("Tela Aviso não apareceu dentro do tempo limite.")
    return False


def _confirmar_popup_confirme(timeout_seconds: int = _CONFIRM_TIMEOUT_SECONDS) -> bool:
    """Wait for the Confirme popup and click OK when it appears."""
    print(f"Aguardando tela Confirme por até {timeout_seconds} segundos...")

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            window = Desktop(backend="win32").window(
                title=_CONFIRM_TITLE,
                class_name=_CONFIRM_CLASS,
            )

            if window.exists(timeout=1):
                window.set_focus()
                time.sleep(0.2)

                ok_button = window.child_window(class_name="TButton", found_index=0)

                if ok_button.exists(timeout=3):
                    ok_button.wait("visible enabled", timeout=3)
                    ok_button.click_input()
                else:
                    pyautogui.press("enter")

                print("Tela Confirme confirmada com OK.")
                return True

        except Exception:
            pass

        time.sleep(1)

    print("Tela Confirme não apareceu dentro do tempo limite.")
    return False


def _fechar_tela_envio_nfe() -> None:
    """Close the Envio/Retorno de NFe em Lotes window."""
    print("Fechando tela Envio/Retorno de NFe em Lotes...")

    window = _obter_tela_envio_nfe(timeout_seconds=5)

    if window is None:
        print("Tela Envio/Retorno já não está aberta.")
        return

    try:
        window.set_focus()
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "f4")
        time.sleep(1)
    except Exception as exc:
        print(f"Falha ao fechar tela Envio/Retorno: {exc}")


def _processar_envio_retorno_nfe() -> bool:
    """Validate the Envio/Retorno screen, execute action, and confirm result."""
    window = _obter_tela_envio_nfe(timeout_seconds=10)

    if window is None:
        print("Tela Envio/Retorno de NFe em Lotes não apareceu.")
        return False

    print("Tela Envio/Retorno de NFe em Lotes localizada.")

    _clicar_botao_envio_nfe(window)

    aviso_confirmado = _confirmar_popup_aviso_erro()

    if aviso_confirmado:
        print("Aviso tratado. Retornando falha para reiniciar Agro.")
        return False

    contagem_enviar_lote = 0

    while True:
        popup_confirmado = _confirmar_popup_enviar_lote_nfs()
        if not popup_confirmado:
            break
        contagem_enviar_lote += 1

    if contagem_enviar_lote > 0:
        print(f"Popup Enviar Lote NFs tratado {contagem_enviar_lote} vez(es) com OK.")
        _fechar_tela_envio_nfe()
        return True

    atencao_confirmado = _confirmar_popup_atencao_nenhuma_nf()

    if atencao_confirmado:
        print("Nenhuma NF selecionada. Indo para próxima nota.")
        _fechar_tela_envio_nfe()
        return True

    confirmado = _confirmar_popup_confirme()

    if not confirmado:
        return False

    _fechar_tela_envio_nfe()
    return True


def run_once(log_id: int | None = None) -> None:
    """Run a continuous processing loop that re-queries notes after each batch.

    When log_id is provided, the platform worker handles task claiming and
    completion. When log_id is None, the legacy main.py path claims the task
    and keeps running until externally interrupted.
    """
    platform_managed = log_id is not None

    if not platform_managed:
        with get_connection() as connection:
            executando = buscar_executando(connection, COMPUTADOR_ROBO)
            if executando:
                print(
                    f"Robô já em execução "
                    f"(log_id={executando['u_robot_log_id']}). Pulando ciclo."
                )
                return

            proximo = buscar_proximo_pendente(connection, COMPUTADOR_ROBO)
            if not proximo:
                print("Nenhuma tarefa pendente na fila.")
                return

            log_id = proximo["u_robot_log_id"]
            marcar_executando(connection, log_id, COMPUTADOR_ROBO)
            print(f"Tarefa log_id={log_id} marcada como EXECUTANDO.")

    agro_iniciado = False
    ultimo_check = time.time()

    while True:
        if time.time() - ultimo_check >= _INTERRUPT_CHECK_INTERVAL:
            if _esta_interrompido():
                print(
                    f"Robô interrompido externamente "
                    f"(log_id={log_id}). Parando processamento."
                )
                return

            ultimo_check = time.time()

        print("\n Buscando notas...")

        with get_connection() as connection:
            notas = buscar_notas_pendentes(connection)

        print(f"Notas encontradas 16: {len(notas)}")

        if not notas:
            print("Nenhuma nota pendente. Aguardando próximo ciclo...")
            time.sleep(20)
            continue

        if not agro_iniciado:
            print("Iniciando Agro...")

            kill_agro_process("Agro3C.exe")
            start_agro(AGRO_EXE)

            time.sleep(5)

            login_agro()
            print("Login realizado.")

            confirm_attention_popup()
            confirm_establishment_selection()

            if not wait_window_startswith("AGRO-AG", timeout_seconds=15):
                raise RuntimeError("Tela AGRO-AG não abriu.")

            print("Agro pronto para uso.")
            agro_iniciado = True

        print("OS.RPA016 workflow iniciado.")

        for nota in notas:
            if time.time() - ultimo_check >= _INTERRUPT_CHECK_INTERVAL:
                if _esta_interrompido():
                    print(
                        f"Robô interrompido externamente "
                        f"(log_id={log_id}). Parando processamento."
                    )
                    return

                ultimo_check = time.time()

            try:
                id_nota = nota.get("U_FISCAL_IO_CONT_ID")
                estab_nota = int(nota["ESTAB"])

                print(f"\n-> Processando nota ID: {id_nota} | Estab: {estab_nota}")

                switched = switch_establishment(estab_nota)

                if not switched:
                    print(
                        f"Tela de seleção de estabelecimento não apareceu para nota "
                        f"{id_nota}. Reiniciando Agro e indo para a próxima."
                    )
                    _reiniciar_agro()
                    continue

                print("Troca de estabelecimento realizada.")

                _abrir_tela_nota_fiscal()

                processed = _processar_envio_retorno_nfe()

                if processed:
                    print("Fluxo Envio/Retorno processado com sucesso.")
                    continue

                print(
                    f"Falha no fluxo Envio/Retorno da nota {id_nota}. "
                    "Reiniciando Agro e indo para a próxima."
                )
                _reiniciar_agro()
                continue

            except Exception as e:
                print(f"Erro na nota {nota.get('U_FISCAL_IO_CONT_ID')}: {e}")
                print("Reiniciando Agro e indo para a próxima.")
                _reiniciar_agro()
                continue


def run() -> None:
    """Run the legacy loop used by main.py."""
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"ERRO GERAL: {e}")

        print("Aguardando 20 segundos...\n")
        time.sleep(20)
