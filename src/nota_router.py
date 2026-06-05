"""Route note processing by NOTACONF.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from __future__ import annotations

from typing import Any

from src.notas.nota_225 import process_notaconf_225
from src.notas.nota_232 import process_notaconf_232
from src.notas.nota_244 import process_notaconf_244
from src.notas.nota_255 import process_notaconf_255
from src.notas.nota_270 import process_notaconf_270
from src.notas.nota_275 import process_notaconf_275
from src.notas.nota_284 import process_notaconf_284
from src.notas.nota_285 import process_notaconf_285
from src.notas.nota_314 import process_notaconf_314

PROCESSORS = {
    "225": process_notaconf_225,
    "232": process_notaconf_232,
    "244": process_notaconf_244,
    "255": process_notaconf_255,
    "270": process_notaconf_270,
    "275": process_notaconf_275,
    "284": process_notaconf_284,
    "285": process_notaconf_285,
    "314": process_notaconf_314,
}


def process_note_by_config(nota: dict[str, Any]) -> bool:
    """Process the note according to its NOTACONF value."""
    notaconf = str(nota.get("NOTACONF", "")).strip()
    processor = PROCESSORS.get(notaconf)

    if not processor:
        print(f"NOTACONF ainda não implementada: {notaconf}")
        return False

    return processor(nota)
