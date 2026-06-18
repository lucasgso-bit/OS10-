"""
Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-05-27
Version: 1.0.0
"""

from __future__ import annotations

from typing import Any

from robots.robot_OS18.src.notas.process_1 import process_1


def process_note_by_config(nota: dict[str, Any]) -> bool:
    return process_1(nota)
