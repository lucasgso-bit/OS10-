"""Agro establishment switching for OS10."""

from __future__ import annotations

import time
import unicodedata

import pyautogui
import pygetwindow as gw


def normalizar_titulo(
    titulo: str,
) -> str:
    """
    Normalize window title for comparison.

    Examples accepted as equivalent:
    AGRO-AG
    AGRO - AG
    Agro - Ag
    """

    titulo = str(
        titulo or ""
    ).strip()

    titulo = unicodedata.normalize(
        "NFKD",
        titulo,
    )

    titulo = "".join(
        caractere
        for caractere in titulo
        if not unicodedata.combining(
            caractere
        )
    )

    titulo = titulo.upper()

    # Remove espaços para facilitar comparação.
    titulo = titulo.replace(
        " ",
        "",
    )

    return titulo


def find_window_startswith(
    title: str,
    timeout_seconds: int = 10,
):
    """
    Find a visible window whose normalized title
    starts with the requested prefix.
    """

    title_normalizado = normalizar_titulo(
        title
    )

    deadline = (
        time.time()
        + timeout_seconds
    )

    while time.time() < deadline:

        try:
            janelas = gw.getAllWindows()

        except Exception as exc:
            print(
                "[OS10] Erro ao listar janelas: "
                f"{exc}"
            )

            time.sleep(0.5)
            continue

        for window in janelas:

            try:
                titulo_janela = str(
                    window.title or ""
                ).strip()

            except Exception:
                continue

            if not titulo_janela:
                continue

            titulo_normalizado = normalizar_titulo(
                titulo_janela
            )

            if not titulo_normalizado.startswith(
                title_normalizado
            ):
                continue

            print(
                "[OS10] Janela encontrada | "
                f"procurado={title} | "
                f"encontrado={titulo_janela}"
            )

            try:
                if window.isMinimized:
                    print(
                        "[OS10] Restaurando janela minimizada."
                    )

                    window.restore()
                    time.sleep(0.3)

            except Exception:
                pass

            try:
                window.activate()
                time.sleep(0.3)

            except Exception as exc:
                print(
                    "[OS10] Janela encontrada, mas não "
                    "foi possível ativá-la | "
                    f"titulo={titulo_janela} | "
                    f"erro={exc}"
                )

            return window

        time.sleep(0.5)

    return None


def wait_window_startswith(
    title: str,
    timeout_seconds: int = 10,
) -> bool:
    """
    Wait until a window starting with
    the requested prefix appears.
    """

    janela = find_window_startswith(
        title=title,
        timeout_seconds=timeout_seconds,
    )

    return janela is not None


def switch_establishment(
    estab: int | str,
    main_title: str = "AGRO-",
) -> bool:
    """
    Switch Agro to requested establishment.

    Supports both the older establishment window
    and the newer Agro establishment window.
    """

    estab = str(
        estab
    ).strip()

    if not estab:
        print(
            "[OS10] ESTAB não informado."
        )

        return False

    # ============================================
    # CONFIRMA TELA PRINCIPAL
    # ============================================

    print(
        "[OS10] Procurando tela principal antes "
        "da troca de estabelecimento | "
        f"prefixo={main_title}"
    )

    if not wait_window_startswith(
        main_title,
        timeout_seconds=20,
    ):
        print(
            "[OS10] Tela principal não encontrada | "
            f"prefixo={main_title}"
        )

        return False

    # ============================================
    # ABRE TROCA DE ESTABELECIMENTO
    # ============================================

    print(
        "[OS10] Comando: SHIFT + F12"
    )

    pyautogui.hotkey(
        "shift",
        "f12",
    )

    time.sleep(1)

    # ============================================
    # VERSÃO ANTIGA
    # ============================================

    print(
        "[OS10] Verificando tela antiga de seleção "
        "de estabelecimento."
    )

    janela_antiga = find_window_startswith(
        "Seleção de Estabelecimento para Trabalho",
        timeout_seconds=3,
    )

    if janela_antiga is not None:

        print(
            "[OS10] Tela antiga encontrada."
        )

        print(
            "[OS10] Comando: CTRL + TAB"
        )

        pyautogui.hotkey(
            "ctrl",
            "tab",
        )

        time.sleep(0.3)

        print(
            "[OS10] Informando estabelecimento | "
            f"ESTAB={estab}"
        )

        pyautogui.write(
            estab,
            interval=0.03,
        )

        time.sleep(0.3)

        print(
            "[OS10] Comando: ENTER"
        )

        pyautogui.press(
            "enter"
        )

        time.sleep(0.3)

        print(
            "[OS10] Comando: ENTER"
        )

        pyautogui.press(
            "enter"
        )

        time.sleep(1)

        print(
            "[OS10] Estabelecimento alterado | "
            f"ESTAB={estab}"
        )

        return True

    # ============================================
    # VERSÃO NOVA
    # ============================================

    print(
        "[OS10] Tela antiga não encontrada. "
        "Verificando versão nova."
    )

    janela_nova = find_window_startswith(
        "Seleção de estabelecimento",
        timeout_seconds=7,
    )

    if janela_nova is None:

        print(
            "[OS10] Nenhuma tela de seleção de "
            "estabelecimento foi encontrada."
        )

        return False

    print(
        "[OS10] Tela nova de seleção de "
        "estabelecimento encontrada."
    )

    # ============================================
    # POSICIONA CAMPO
    # ============================================

    print(
        "[OS10] Comando: HOME"
    )

    pyautogui.press(
        "home"
    )

    time.sleep(0.3)

    print(
        "[OS10] Comando: SHIFT + TAB"
    )

    pyautogui.hotkey(
        "shift",
        "tab",
    )

    time.sleep(0.3)

    # ============================================
    # DIGITA ESTAB
    # ============================================

    print(
        "[OS10] Informando estabelecimento | "
        f"ESTAB={estab}"
    )

    pyautogui.write(
        estab,
        interval=0.03,
    )

    time.sleep(0.3)

    # ============================================
    # CONFIRMA
    # ============================================

    print(
        "[OS10] Comando: TAB"
    )

    pyautogui.press(
        "tab"
    )

    time.sleep(0.3)

    print(
        "[OS10] Comando: ENTER"
    )

    pyautogui.press(
        "enter"
    )

    time.sleep(1)

    # ============================================
    # CONFIRMA QUE VOLTOU PARA O AGRO
    # ============================================

    print(
        "[OS10] Aguardando retorno para tela principal."
    )

    voltou_agro = wait_window_startswith(
        main_title,
        timeout_seconds=15,
    )

    if not voltou_agro:
        print(
            "[OS10] Estabelecimento foi informado, "
            "mas a tela principal não reapareceu."
        )

        return False

    print(
        "[OS10] Estabelecimento alterado com sucesso | "
        f"ESTAB={estab}"
    )

    return True