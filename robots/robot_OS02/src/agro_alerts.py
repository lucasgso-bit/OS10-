"""Agro popup handling for OS20."""

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
