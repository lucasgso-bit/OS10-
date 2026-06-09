"""Route note processing by NOTACONF.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-08
Version: 1.0.0
"""

from __future__ import annotations

from typing import Any

# TODO: importar os processadores de cada nota quando implementados
# from robots.robot_OS16.src.notas.nota_XXX import process_notaconf_XXX

PROCESSORS: dict[str, Any] = {
    # "XXX": process_notaconf_XXX,
}


def process_note_by_config(nota: dict[str, Any]) -> bool:
    """Process the note according to its NOTACONF value."""
    notaconf = str(nota.get("NOTACONF", "")).strip()
    processor = PROCESSORS.get(notaconf)

    if not processor:
        print(f"NOTACONF ainda não implementada: {notaconf}")
        return False

    return processor(nota)
