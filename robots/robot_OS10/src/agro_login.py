"""Agro login automation for OS10 with execution logs."""

from __future__ import annotations

import time

import pyautogui
import win32con
import win32gui
from pywinauto import Desktop

from config import AGRO_SENHA


OS10_AGRO_USUARIO = "RPA.OS10"

_LOGIN_WINDOW_TITLE = "Seleção de Usuário"
_LOGIN_WINDOW_CLASS = "TFSelUsu"
_LOGIN_TIMEOUT_SECONDS = 20

_ATENCAO_TITLE = "Atenção!"
_ATENCAO_CLASS = "TFRes"
_ATENCAO_TIMEOUT_SECONDS = 10


def _wait_atencao_window(timeout_seconds: int = _ATENCAO_TIMEOUT_SECONDS):
    print(
        "[OS10] Verificando tela Atenção | "
        f"TITLE={_ATENCAO_TITLE} | CLASS={_ATENCAO_CLASS}"
    )

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            hwnd = win32gui.FindWindow(
                _ATENCAO_CLASS,
                _ATENCAO_TITLE,
            )

            if hwnd and win32gui.IsWindowVisible(hwnd):
                print(
                    "[OS10] Tela Atenção encontrada | "
                    f"HWND={hwnd}"
                )
                return hwnd

        except Exception as exc:
            print(
                f"[OS10] Erro ao procurar tela Atenção: {exc}"
            )

        time.sleep(0.3)

    return None


def _fechar_atencao_se_existir() -> bool:
    hwnd = _wait_atencao_window()

    if not hwnd:
        print("[OS10] Tela Atenção não apareceu.")
        return False

    print("[OS10] Focando tela Atenção.")

    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(
                hwnd,
                win32con.SW_RESTORE,
            )
            time.sleep(0.3)

        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)

    except Exception as exc:
        raise RuntimeError(
            f"Não foi possível focar a tela Atenção: {exc}"
        ) from exc

    time.sleep(0.5)

    hwnd_ativo = win32gui.GetForegroundWindow()
    classe_ativa = win32gui.GetClassName(hwnd_ativo)
    titulo_ativo = win32gui.GetWindowText(hwnd_ativo).strip()

    print(
        "[OS10] Conferência da tela Atenção | "
        f"CLASS={classe_ativa} | "
        f"TITULO={titulo_ativo}"
    )

    if (
        hwnd_ativo != hwnd
        or classe_ativa != _ATENCAO_CLASS
    ):
        raise RuntimeError(
            "A tela Atenção foi encontrada, "
            "mas não ficou em foco."
        )

    print("[OS10] Fechando tela Atenção com ENTER.")

    for tentativa in range(1, 4):
        # Confirma novamente o foco imediatamente antes de cada ENTER.
        hwnd_antes_enter = win32gui.FindWindow(
            _ATENCAO_CLASS,
            _ATENCAO_TITLE,
        )

        if not (
            hwnd_antes_enter
            and win32gui.IsWindowVisible(hwnd_antes_enter)
        ):
            break

        try:
            win32gui.BringWindowToTop(hwnd_antes_enter)
            win32gui.SetForegroundWindow(hwnd_antes_enter)
        except Exception as exc:
            print(
                "[OS10] Erro ao refocar Atenção antes do ENTER | "
                f"tentativa={tentativa} | {exc}"
            )

        time.sleep(0.3)

        hwnd_foco = win32gui.GetForegroundWindow()

        if hwnd_foco != hwnd_antes_enter:
            raise RuntimeError(
                "Atenção não está em foco antes do ENTER. "
                f"HWND esperado={hwnd_antes_enter} | "
                f"HWND ativo={hwnd_foco}"
            )

        print(
            "[OS10] ENTER na tela Atenção | "
            f"tentativa={tentativa}/3 | HWND={hwnd_antes_enter}"
        )

        pyautogui.press("enter")

        time.sleep(1)

        # Validação real: a mesma tela precisa ter desaparecido.
        hwnd_restante = win32gui.FindWindow(
            _ATENCAO_CLASS,
            _ATENCAO_TITLE,
        )

        if not (
            hwnd_restante
            and win32gui.IsWindowVisible(hwnd_restante)
        ):
            print(
                "[OS10] ENTER confirmado: "
                "tela Atenção fechada."
            )
            return True

        print(
            "[OS10] Atenção ainda aberta após ENTER. "
            "Nova tentativa."
        )

    raise RuntimeError(
        "A tela Atenção não fechou após três tentativas de ENTER."
    )


def _wait_login_window(timeout_seconds: int = _LOGIN_TIMEOUT_SECONDS):
    print(
        "[OS10] Aguardando tela de login | "
        f"TITLE={_LOGIN_WINDOW_TITLE} | CLASS={_LOGIN_WINDOW_CLASS}"
    )

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            window = Desktop(backend="win32").window(
                title=_LOGIN_WINDOW_TITLE,
                class_name=_LOGIN_WINDOW_CLASS,
            )

            if window.exists(timeout=1):
                window.set_focus()
                print("[OS10] Tela de login encontrada.")
                return window

        except Exception:
            pass

        time.sleep(0.5)

    raise RuntimeError(
        "Tela 'Seleção de Usuário' não apareceu no login do Agro."
    )


def _fill_control(window, class_name: str, value: str, field_name: str):
    try:
        print(
            f"[OS10] Localizando campo {field_name} | CLASS={class_name}"
        )

        control = window.child_window(
            class_name=class_name,
            found_index=0,
        )

        if not control.exists(timeout=5):
            raise RuntimeError(
                f"Campo {field_name} não apareceu."
            )

        control.wait("visible enabled", timeout=5)
        control.click_input()

        time.sleep(0.2)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)

        pyautogui.write(
            value,
            interval=0.03,
        )

        print(
            f"[OS10] Campo {field_name} preenchido."
        )

    except Exception as exc:
        raise RuntimeError(
            f"Não foi possível preencher o campo {field_name}."
        ) from exc


def login_agro(
    usuario: str = OS10_AGRO_USUARIO,
    senha: str = AGRO_SENHA,
) -> None:
    print("[OS10] Iniciando preenchimento do login.")

    if not usuario:
        raise ValueError("Usuário do Agro não informado.")

    if not senha:
        raise ValueError("Senha do Agro não informada.")

    # O Agro pode abrir uma tela "Atenção!" na frente da tela de login.
    # Nesse caso, primeiro fecha o modal para liberar a tela TFSelUsu.
    _fechar_atencao_se_existir()

    window = _wait_login_window()

    print(f"[OS10] Informando usuário: {usuario}")

    _fill_control(
        window=window,
        class_name="Edit",
        value=usuario,
        field_name="Usuário",
    )

    _fill_control(
        window=window,
        class_name="TEdit",
        value=senha,
        field_name="Senha",
    )

    time.sleep(0.5)

    window.set_focus()

    print("[OS10] Confirmando login com ENTER.")

    pyautogui.press("enter")

    time.sleep(2)

    print("[OS10] Login enviado.")
