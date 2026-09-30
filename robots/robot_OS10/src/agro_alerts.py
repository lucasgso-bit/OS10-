from __future__ import annotations

import time

import pyautogui
import pygetwindow as gw


def confirm_attention_popup(timeout_seconds: int = 10) -> bool:
    """Confirm the 'Atenção!' popup if it appears."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if gw.getWindowsWithTitle("Atenção!"):
            time.sleep(0.5)
            pyautogui.press("enter")
            print("Popup 'Atenção!' confirmado.")
            return True
        time.sleep(0.5)
    return False


def confirm_establishment_selection(timeout_seconds: int = 10) -> bool:
    """Confirm the establishment selection window if it appears."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if gw.getWindowsWithTitle("Seleção de Estabelecimento para Trabalho"):
            time.sleep(0.5)
            for _ in range(4):
                pyautogui.press("enter")
                time.sleep(0.2)
            print("Tela 'Seleção de Estabelecimento para Trabalho' confirmada.")
            return True
        time.sleep(0.5)
    return False


##### versão do novo agro ######

# from __future__ import annotations

# import time

# import pyautogui
# import pygetwindow as gw
# from pywinauto import Desktop

# ATTENTION_POPUP_TITLE = "Atenção!"

# ESTABLISHMENT_WINDOW_TITLE = "Seleção de estabelecimento"
# ESTABLISHMENT_WINDOW_CLASS = "TfmSelEmp"


# def confirm_attention_popup(timeout_seconds: int = 10) -> bool:
#     """Confirma o popup 'Atenção!' caso ele apareça."""
#     deadline = time.time() + timeout_seconds

#     while time.time() < deadline:
#         windows = gw.getWindowsWithTitle(ATTENTION_POPUP_TITLE)

#         if windows:
#             try:
#                 windows[0].activate()
#             except Exception:
#                 pass

#             time.sleep(0.5)
#             pyautogui.press("enter")

#             print("[OS10] Popup 'Atenção!' confirmado.")
#             return True

#         time.sleep(0.5)

#     print("[OS10] Popup 'Atenção!' não apareceu.")
#     return False


# def confirm_establishment_selection(
#     timeout_seconds: int = 15,
# ) -> bool:
#     """Confirma a tela de seleção de estabelecimento."""
#     print(
#         "[OS10] Aguardando tela de seleção de estabelecimento "
#         f"title={ESTABLISHMENT_WINDOW_TITLE!r} "
#         f"class={ESTABLISHMENT_WINDOW_CLASS!r}"
#     )

#     deadline = time.time() + timeout_seconds
#     last_error: Exception | None = None

#     while time.time() < deadline:
#         try:
#             window = Desktop(backend="win32").window(
#                 title=ESTABLISHMENT_WINDOW_TITLE,
#                 class_name=ESTABLISHMENT_WINDOW_CLASS,
#             )

#             if not window.exists(timeout=1):
#                 time.sleep(0.5)
#                 continue

#             window.wait(
#                 "visible enabled",
#                 timeout=5,
#             )

#             window.set_focus()
#             time.sleep(0.5)

#             print("[OS10] Tela de seleção de estabelecimento encontrada.")

#             pyautogui.press("tab")
#             time.sleep(0.2)

#             pyautogui.press("enter")
#             time.sleep(0.5)

#             print("[OS10] Tela 'Seleção de estabelecimento' confirmada.")

#             return True

#         except Exception as exc:
#             last_error = exc
#             time.sleep(0.5)

#     error_message = (
#         "Tela de seleção de estabelecimento não apareceu. "
#         f"Esperado: title={ESTABLISHMENT_WINDOW_TITLE!r}, "
#         f"class={ESTABLISHMENT_WINDOW_CLASS!r}."
#     )

#     if last_error is not None:
#         print(f"[OS10] {error_message} Último erro: {last_error}")
#     else:
#         print(f"[OS10] {error_message}")

#     return False
