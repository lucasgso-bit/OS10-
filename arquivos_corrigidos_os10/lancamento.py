"""
OS10 launch module.

Open Agro, switch establishment, open Nota Fiscal screen and start a new note
with CTRL + INSERT.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-07-08
Version: 1.0.1
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import pyautogui
import psutil
import pygetwindow as gw
import win32con
import win32gui
import win32clipboard
from pywinauto import Desktop

from .agro_estab import switch_establishment, wait_window_startswith
from .notifier import notify_conclusao_os10, notify_erro_os10
from .fiscal_retencao import analisar_retencoes, RetencaoImposto
from .agro_login import login_agro

SCREENSHOT_DIR = r"C:\XML_NFSE\Screen"
AGRO_EXE = os.getenv("AGRO_EXE", "")

# Pequena pausa global entre ações de teclado/mouse.
# Mantém a mesma lógica, apenas reduz a velocidade para dar mais
# tempo ao Agro entre uma ação e outra.
pyautogui.PAUSE = 0.12


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _valor(nota: dict[str, Any], campo: str, default: str = "") -> str:
    """Return normalized value from note by database column name."""
    valor = nota.get(campo)

    if valor is None:
        return default

    return str(valor).strip()


def _write_value(nome: str, valor: str, interval: float = 0.03) -> None:
    """Write a value on screen and log it."""
    if not valor:
        raise RuntimeError(f"Valor não informado para: {nome}")

    print(f"[OS10] Enviando variável {nome}: {valor}")
    pyautogui.write(valor, interval=interval)
    _sleep(0.5)


def formatar_data_emissao(data: str) -> str:
    """Format date from DD/MM/YYYY to DDMMYY."""
    data = str(data or "").strip()

    if len(data) < 10:
        raise RuntimeError(f"Data de emissão inválida: {data}")

    return data[0:2] + data[3:5] + data[-2:]


def _click_button_by_class_instance(
    parent_title: str,
    class_name: str,
    instance: int = 1,
    label: str | None = None,
) -> None:
    """Click a child button by class and instance without using coordinates."""
    parent_hwnd = _find_window_startswith(parent_title)

    if not parent_hwnd:
        raise RuntimeError(f"Janela pai não encontrada: {parent_title}")

    matches: list[int] = []

    def enum_child(hwnd: int, _: object) -> None:
        if win32gui.GetClassName(hwnd) == class_name:
            matches.append(hwnd)

    win32gui.EnumChildWindows(parent_hwnd, enum_child, None)

    button_label = label or f"CLASS:{class_name}, INSTANCE:{instance}"

    if len(matches) < instance:
        raise RuntimeError(
            f"Botão não encontrado:{button_label} | CLASS:{class_name}, INSTANCE:{instance}"
        )

    button_hwnd = matches[instance - 1]

    print(f"[OS03] Acionando botão {button_label}")
    win32gui.PostMessage(button_hwnd, win32con.BM_CLICK, 0, 0)
    _sleep(1)


def _find_window_startswith(title_prefix: str) -> int | None:
    """Find a visible window whose title starts with the given prefix."""
    found_hwnd: int | None = None

    def enum_window(hwnd: int, _: object) -> None:
        nonlocal found_hwnd

        if found_hwnd is not None:
            return

        if not win32gui.IsWindowVisible(hwnd):
            return

        title = win32gui.GetWindowText(hwnd).strip()

        if title.startswith(title_prefix):
            found_hwnd = hwnd

    win32gui.EnumWindows(enum_window, None)
    return found_hwnd


def tirar_print_erro(nota: dict[str, Any]) -> str | None:
    """Take screenshot for OS10 error."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    numero_nota = (
        _valor(nota, "NUMERO_NF")
        or _valor(nota, "NOTATERC")
        or _valor(nota, "NUM_PED")
        or "sem_nota"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(
        SCREENSHOT_DIR,
        f"erro_os10_{numero_nota}_{timestamp}.png",
    )

    try:
        pyautogui.screenshot(screenshot_path)
        print(f"[OS10] Screenshot de erro salvo: {screenshot_path}")
        return screenshot_path
    except Exception as print_exc:
        print(f"[OS10] Erro ao tirar screenshot de erro: {print_exc}")
        return None


def executar_lancamento(
    notas: list[dict[str, Any]],
    task: dict[str, Any],
    log_id: int,
) -> None:
    """Execute OS10 initial launch flow for pending notes."""
    _ = task

    print(f"[OS10] Iniciando lançamento | log_id={log_id}")
    print(f"[OS10] Total de notas para lançar: {len(notas)}")

    relatorio_final: list[dict[str, Any]] = []

    if not notas:
        print("[OS10] Nenhuma nota pendente encontrada.")
        return

    for nota in notas:
        try:
            _processar_lancamento(nota)

            relatorio_final.append(
                montar_linha_relatorio_final(
                    nota=nota,
                    mensagem="Nota Fiscal aberta com sucesso até CTRL + INSERT.",
                )
            )

        except Exception as exc:
            print(
                "[OS10] ERRO COMPLETO:",
                repr(exc)
            )

            motivo = str(exc)

            relatorio_final.append(
                montar_linha_relatorio_final(
                    nota=nota,
                    mensagem=f"ERRO: {motivo}",
                )
            )

            linha_erro = montar_linha_relatorio_erro(
                nota=nota,
                mensagem=motivo,
            )

            screenshot_path = tirar_print_erro(nota)

            notify_erro_os10(
                nota=linha_erro,
                motivo=motivo,
                screenshot_path=screenshot_path,
            )

            print(f"[OS10] Erro ao processar nota. Erro: {motivo}")

            # Evita iniciar a próxima nota com Pagamento/Acerto/Nota Fiscal
            # ainda abertos. Isso foi a causa da falha subsequente no
            # SHIFT+F12 quando uma nota anterior parou no financeiro.
            try:
                classes_transacao = (
                    "TFPlacaVeiculos",
                    "TFrGerarNFFrota",
                    "TFPagCompraDupPag",
                    "TFAcertoFinanceiro",
                    "TFNfCab",
                )

                if any(
                    _janela_visivel_por_classe(class_name)
                    for class_name in classes_transacao
                ):
                    print(
                        "[OS10] Erro deixou telas transacionais abertas. "
                        "Executando limpeza antes da próxima nota."
                    )
                    fechar_telas_lancamento()

            except Exception as cleanup_exc:
                print(
                    "[OS10] Não foi possível concluir a limpeza "
                    f"das telas após o erro: {cleanup_exc}"
                )

            continue

    if relatorio_final:
        notify_conclusao_os10(relatorio_final)

    print("[OS10] Processo finalizado.")


def _to_float(valor: str) -> float:
    """Convert monetary text to float accepting comma or dot decimals."""
    texto = str(valor or "").strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto and "." in texto:
        # Exemplo: 1.234,56
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        # Exemplo: 1234,56
        texto = texto.replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return 0.0


def _is_zero_value(valor: str) -> bool:
    """Check if monetary value is empty or zero."""
    return _to_float(valor) == 0.0


def _candidatos_valor_duplicata(
    dados: dict[str, str],
) -> list[tuple[str, float]]:
    """
    Return possible expected payment totals for Pagamento com Duplicatas.

    VALOR_LIQUIDO remains the primary database reference.

    For RETPISCOFINS=3 the current OS10 data uses VALOR_CSLL as the
    consolidated PIS/COFINS/CSLL retention amount. This is why individual
    VALOR_PIS and VALOR_COFINS must not be subtracted again in that case.

    Other candidates are only added when their source value is available.
    """
    candidatos: list[tuple[str, float]] = []

    valor_liquido = round(
        _to_float(dados.get("VALOR_LIQUIDO", "")),
        2,
    )

    if valor_liquido > 0:
        candidatos.append(
            ("VALOR_LIQUIDO", valor_liquido)
        )

    valor_total_nf = round(
        _to_float(dados.get("VALOR_TOTAL_NF", "")),
        2,
    )

    valor_retencao = round(
        _to_float(dados.get("VALOR_RETENCAO", "")),
        2,
    )

    if valor_total_nf > 0 and valor_retencao > 0:
        candidatos.append(
            (
                "VALOR_TOTAL_NF - VALOR_RETENCAO",
                round(valor_total_nf - valor_retencao, 2),
            )
        )

    # Caso observado no fluxo atual:
    # RETPISCOFINS=3 representa retenção conjunta de PIS/COFINS/CSLL.
    # VALOR_CSLL contém o total consolidado dessa retenção.
    retpiscofins = str(
        dados.get("RETPISCOFINS", "") or ""
    ).strip()

    if valor_total_nf > 0 and retpiscofins == "3":
        valor_irrf = round(
            _to_float(dados.get("VALOR_IRRF", "")),
            2,
        )

        valor_pcc = round(
            _to_float(dados.get("VALOR_CSLL", "")),
            2,
        )

        valor_inss = round(
            _to_float(dados.get("VALOR_INSS", "")),
            2,
        )

        retissqn = str(
            dados.get("RETISSQN", "") or ""
        ).strip()

        valor_iss = 0.0

        # No fluxo atual RETISSQN=1 significa ISS não retido.
        if retissqn and retissqn != "1":
            valor_iss = round(
                _to_float(dados.get("VALOR_ISSQN", "")),
                2,
            )

        total_retencoes_financeiras = round(
            valor_irrf
            + valor_pcc
            + valor_inss
            + valor_iss,
            2,
        )

        if total_retencoes_financeiras > 0:
            candidatos.append(
                (
                    "VALOR_TOTAL_NF - RETENCOES_FINANCEIRAS",
                    round(
                        valor_total_nf
                        - total_retencoes_financeiras,
                        2,
                    ),
                )
            )

    # Remove candidatos duplicados pelo valor, preservando a ordem.
    unicos: list[tuple[str, float]] = []
    valores_adicionados: set[float] = set()

    for origem, valor in candidatos:
        valor = round(valor, 2)

        if valor in valores_adicionados:
            continue

        valores_adicionados.add(valor)
        unicos.append((origem, valor))

    return unicos


def _validar_valor_duplicata(
    total_produtos: str,
    dados: dict[str, str],
) -> tuple[float, float, str]:
    """
    Compare the screen total against supported expected values.

    Returns:
        (expected_value, absolute_difference, source_description)
    """
    total_tela = round(
        _to_float(total_produtos),
        2,
    )

    candidatos = _candidatos_valor_duplicata(
        dados
    )

    if not candidatos:
        raise RuntimeError(
            "Não foi possível calcular um valor esperado "
            "para Pagamento com Duplicatas."
        )

    print(
        f"[OS10] Total Produtos tela: {total_produtos} "
        f"({total_tela:.2f})"
    )

    melhor_origem = ""
    melhor_valor = 0.0
    melhor_diferenca = float("inf")

    for origem, valor_esperado in candidatos:
        diferenca = round(
            abs(total_tela - valor_esperado),
            2,
        )

        print(
            "[OS10] Candidato duplicata | "
            f"Origem={origem} | "
            f"Esperado={valor_esperado:.2f} | "
            f"Diferença={diferenca:.2f}"
        )

        if diferenca < melhor_diferenca:
            melhor_origem = origem
            melhor_valor = valor_esperado
            melhor_diferenca = diferenca

    print(
        "[OS10] Melhor referência da duplicata | "
        f"Origem={melhor_origem} | "
        f"Esperado={melhor_valor:.2f} | "
        f"Diferença={melhor_diferenca:.2f}"
    )

    return (
        melhor_valor,
        melhor_diferenca,
        melhor_origem,
    )


def _format_decimal_br(valor: float) -> str:
    """Format decimal value using comma separator."""
    return f"{valor:.2f}".replace(".", ",")


def _set_clipboard_text(texto: str) -> None:
    """Set Windows clipboard text."""
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(texto, win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


def _get_clipboard_text() -> str:
    """Get Windows clipboard text."""
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                return str(
                    win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                ).strip()
        finally:
            win32clipboard.CloseClipboard()
    except Exception as exc:
        print(f"[OS10] Erro ao ler clipboard: {exc}")

    return ""


def somar_centavos_no_campo_selecionado(qtd_centavos: int) -> None:
    """Add cents to the currently selected field and press ENTER."""
    if qtd_centavos <= 0:
        return

    _set_clipboard_text("")
    _sleep(0.1)

    print("[OS10] Comando: CTRL + C")
    pyautogui.hotkey("ctrl", "c")
    _sleep(0.2)

    valor_atual_texto = _get_clipboard_text()
    valor_atual_numero = _to_float(valor_atual_texto)

    valor_novo_numero = valor_atual_numero + (qtd_centavos / 100)
    valor_novo_texto = _format_decimal_br(valor_novo_numero)

    print(
        "[OS10] Ajustando centavos | "
        f"valor_atual={valor_atual_texto} | "
        f"qtd_centavos={qtd_centavos} | "
        f"valor_novo={valor_novo_texto}"
    )

    pyautogui.hotkey("ctrl", "a")
    _sleep(0.1)

    pyautogui.write(valor_novo_texto, interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.4)


def ir_para_campo_pis_ajuste_centavos() -> None:
    """Move cursor to PIS value field for cents adjustment."""
    print("[OS10] Indo para campo PIS.")

    pyautogui.press("right", presses=4, interval=0.2)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.4)


def ir_para_proximo_imposto_ajuste_centavos() -> None:
    """Move cursor to next tax value field."""
    print("[OS10] Indo para próximo imposto.")

    pyautogui.press("down")
    _sleep(0.2)

    pyautogui.press("left")
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.4)


def ajustar_centavos_pis_cofins_csll(diferenca: float) -> None:
    """Distribute cents difference between PIS, COFINS and CSLL."""
    qtd_centavos = int(round(abs(diferenca) * 100))

    if qtd_centavos <= 0:
        print("[OS10] Sem diferença de centavos para ajustar.")
        return

    add_pis = (qtd_centavos + 2) // 3
    add_cofins = (qtd_centavos + 1) // 3
    add_csll = qtd_centavos // 3

    print(
        "[OS10] Distribuindo diferença de centavos | "
        f"qtd_centavos={qtd_centavos} | "
        f"PIS={add_pis} | "
        f"COFINS={add_cofins} | "
        f"CSLL={add_csll}"
    )

    ir_para_campo_pis_ajuste_centavos()

    if add_pis > 0:
        print("[OS10] Ajustando PIS.")
        somar_centavos_no_campo_selecionado(add_pis)

    if add_cofins > 0:
        print("[OS10] Ajustando COFINS.")
        ir_para_proximo_imposto_ajuste_centavos()
        somar_centavos_no_campo_selecionado(add_cofins)

    if add_csll > 0:
        print("[OS10] Ajustando CSLL.")
        ir_para_proximo_imposto_ajuste_centavos()
        somar_centavos_no_campo_selecionado(add_csll)

    print("[OS10] Ajuste de centavos concluído.")


def _voltar_grid() -> None:
    """Return to the first row of the retention grid."""
    print("[OS10] Comando: HOME")
    pyautogui.press("home")
    _sleep(0.5)

    print("[OS10] Comando: DOWN 2x")
    pyautogui.press("down", presses=2, interval=0.2)
    _sleep(0.5)

    print("[OS10] Comando: RIGHT 2x")
    pyautogui.press("right", presses=2, interval=0.2)
    _sleep(0.5)


def validar_irrf(dados: dict[str, str], decisao: RetencaoImposto | None = None) -> None:
    """Validate and fill IRRF retention fields."""
    valor_irrf_original = dados["VALOR_IRRF"]
    valor_total_nf_original = dados["VALOR_TOTAL_NF"]

    print(
        "[OS10] Validando IRRF | "
        f"VALOR_IRRF={valor_irrf_original} | "
        f"VALOR_TOTAL_NF={valor_total_nf_original}"
    )

    if _is_zero_value(valor_irrf_original):
        print("[OS10] IRRF zerado. Preenchendo fluxo sem retenção.")

        pyautogui.press("enter")
        _sleep(0.1)

        pyautogui.write("0", interval=0.03)
        _sleep(0.1)

        pyautogui.press("enter")
        _sleep(0.1)

        pyautogui.press("enter", presses=4, interval=0.1)
        _sleep(0.1)

        pyautogui.write("090", interval=0.03)
        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("up")
        _sleep(0.2)

        return

    print("[OS10] IRRF encontrado. Calculando alíquota.")

    valor_total_nf = _to_float(valor_total_nf_original)
    valor_irrf = _to_float(valor_irrf_original)

    aliquota = 0.0
    if valor_total_nf > 0:
        aliquota = (valor_irrf / valor_total_nf) * 100

    aliquota_str = _format_decimal_br(aliquota)

    print(
        "[OS10] IRRF calculado | "
        f"BASE={valor_total_nf_original} | "
        f"ALIQUOTA={aliquota_str} | "
        f"VALOR_IRRF={valor_irrf_original}"
    )

    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("VALOR_TOTAL_NF", valor_total_nf_original)
    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("ALIQUOTA_IRRF", aliquota_str)
    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("VALOR_IRRF", valor_irrf_original)
    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0,00", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0,00", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("000", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("up")
    _sleep(0.2)


def validar_pis(dados: dict[str, str], decisao: RetencaoImposto | None = None) -> None:
    """Validate and fill PIS retention fields."""
    valor_pis = dados["VALOR_PIS"]
    valor_csll = dados["VALOR_CSLL"]
    retpiscofins = dados["RETPISCOFINS"]
    valor_total_nf = dados["VALOR_TOTAL_NF"]

    print(
        "[OS10] Validando PIS | "
        f"VALOR_PIS={valor_pis} | "
        f"VALOR_CSLL={valor_csll} | "
        f"RETPISCOFINS={retpiscofins} | "
        f"VALOR_TOTAL_NF={valor_total_nf}"
    )

    codigos_pis_retido = {"1", "3", "4", "5", "9"}

    forcar_pis_retido = retpiscofins == "3" and not _is_zero_value(valor_csll)

    if retpiscofins in codigos_pis_retido:
        if _is_zero_value(valor_pis) and not forcar_pis_retido:
            print("[OS10] Código indica PIS retido, mas VALOR_PIS está zerado.")

            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.write("0", interval=0.03)
            _sleep(0.2)

            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.press("enter", presses=4, interval=0.2)
            _sleep(0.2)

            pyautogui.write("090", interval=0.03)
            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.press("up")
            _sleep(0.2)

            return

        print("[OS10] PIS retido. Preenchendo base e alíquota.")

        pyautogui.press("enter")
        _sleep(0.2)

        _write_value("VALOR_TOTAL_NF", valor_total_nf)
        pyautogui.press("enter")
        _sleep(0.2)

        _write_value("ALIQUOTA_PIS", "0,65")
        pyautogui.press("enter")
        _sleep(0.2)

        # Mantido igual ao AutoIt:
        # o sistema calcula o valor do PIS sozinho.
        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("0,00", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("0,00", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("000", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("up")
        _sleep(0.2)

        return

    print("[OS10] PIS não retido. Lançando zerado.")

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("enter", presses=4, interval=0.2)
    _sleep(0.2)

    pyautogui.write("090", interval=0.03)
    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("up")
    _sleep(0.2)


def validar_cofins(
    dados: dict[str, str], decisao: RetencaoImposto | None = None
) -> None:
    """Validate and fill COFINS retention fields."""
    valor_cofins = dados["VALOR_COFINS"]
    valor_csll = dados["VALOR_CSLL"]
    retpiscofins = dados["RETPISCOFINS"]
    valor_total_nf = dados["VALOR_TOTAL_NF"]

    print(
        "[OS10] Validando COFINS | "
        f"VALOR_COFINS={valor_cofins} | "
        f"VALOR_CSLL={valor_csll} | "
        f"RETPISCOFINS={retpiscofins} | "
        f"VALOR_TOTAL_NF={valor_total_nf}"
    )

    codigos_cofins_retido = {"1", "3", "4", "6", "7"}

    forcar_cofins_retido = retpiscofins == "3" and not _is_zero_value(valor_csll)

    if retpiscofins in codigos_cofins_retido:
        if _is_zero_value(valor_cofins) and not forcar_cofins_retido:
            print("[OS10] Código indica COFINS retido, mas VALOR_COFINS está zerado.")

            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.write("0", interval=0.03)
            _sleep(0.2)

            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.press("enter", presses=4, interval=0.2)
            _sleep(0.2)

            pyautogui.write("090", interval=0.03)
            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.press("up")
            _sleep(0.2)

            return

        print("[OS10] COFINS retido. Preenchendo base e alíquota.")

        pyautogui.press("enter")
        _sleep(0.2)

        _write_value("VALOR_TOTAL_NF", valor_total_nf)
        pyautogui.press("enter")
        _sleep(0.2)

        _write_value("ALIQUOTA_COFINS", "3,00")
        pyautogui.press("enter")
        _sleep(0.2)

        # Mantido igual ao AutoIt:
        # o sistema calcula o valor do COFINS sozinho.
        # Se precisar informar manualmente, use:
        # _write_value("VALOR_COFINS", valor_cofins)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("0,00", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("0,00", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("000", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("up")
        _sleep(0.2)

        return

    print("[OS10] COFINS não retido. Lançando zerado.")

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("enter", presses=4, interval=0.2)
    _sleep(0.2)

    pyautogui.write("090", interval=0.03)
    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("up")
    _sleep(0.2)


def validar_csll(dados: dict[str, str], decisao: RetencaoImposto | None = None) -> None:
    """Validate and fill CSLL retention fields."""
    valor_csll = dados["VALOR_CSLL"]
    retpiscofins = dados["RETPISCOFINS"]
    valor_total_nf = dados["VALOR_TOTAL_NF"]

    print(
        "[OS10] Validando CSLL | "
        f"VALOR_CSLL={valor_csll} | "
        f"RETPISCOFINS={retpiscofins} | "
        f"VALOR_TOTAL_NF={valor_total_nf}"
    )

    codigos_csll_retido = {"1", "3", "7", "8", "9"}

    if retpiscofins in codigos_csll_retido:
        if _is_zero_value(valor_csll):
            print("[OS10] Código indica CSLL retido, mas VALOR_CSLL está zerado.")

            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.write("0", interval=0.03)
            _sleep(0.2)

            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.press("enter", presses=4, interval=0.2)
            _sleep(0.2)

            pyautogui.write("090", interval=0.03)
            pyautogui.press("enter")
            _sleep(0.2)

            pyautogui.press("up")
            _sleep(0.2)

            return

        print("[OS10] CSLL retido. Preenchendo base e alíquota.")

        pyautogui.press("enter")
        _sleep(0.2)

        _write_value("VALOR_TOTAL_NF", valor_total_nf)
        pyautogui.press("enter")
        _sleep(0.2)

        _write_value("ALIQUOTA_CSLL", "1,00")
        pyautogui.press("enter")
        _sleep(0.2)

        # Mantido igual ao AutoIt:
        # o sistema calcula o valor do CSLL sozinho.
        # Se precisar informar manualmente, use:
        # _write_value("VALOR_CSLL", valor_csll)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("0", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("0", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("000", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("up")
        _sleep(0.2)

        return

    print("[OS10] CSLL não retido. Lançando zerado.")

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("enter", presses=4, interval=0.2)
    _sleep(0.2)

    pyautogui.write("090", interval=0.03)
    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("up")
    _sleep(0.2)


def validar_iss(dados: dict[str, str], decisao: RetencaoImposto | None = None) -> None:
    """Validate and fill ISSQN retention fields."""
    valor_issqn = dados["VALOR_ISSQN"]
    retissqn = dados["RETISSQN"]
    valor_total_nf = dados["VALOR_TOTAL_NF"]
    aliqissqn = dados["ALIQISSQN"]

    print(
        "[OS10] Validando ISSQN | "
        f"VALOR_ISSQN={valor_issqn} | "
        f"RETISSQN={retissqn} | "
        f"VALOR_TOTAL_NF={valor_total_nf} | "
        f"ALIQISSQN={aliqissqn}"
    )

    if _is_zero_value(valor_issqn) or retissqn == "1" or not retissqn:
        print("[OS10] ISSQN não retido ou zerado. Lançando zerado.")

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.write("0", interval=0.03)
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("enter", presses=4, interval=0.2)
        _sleep(0.2)

        pyautogui.write("090", interval=0.03)
        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("up")
        _sleep(0.2)

        return

    print("[OS10] ISSQN retido. Preenchendo base, alíquota e valor.")

    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("VALOR_TOTAL_NF", valor_total_nf)
    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("ALIQISSQN", aliqissqn)
    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("VALOR_ISSQN", valor_issqn)
    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0,00", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0,00", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("000", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("up")
    _sleep(0.2)


def _format_decimal_br_1(valor: float) -> str:
    """Format decimal value with one decimal place using comma separator."""
    return f"{valor:.1f}".replace(".", ",")


def validar_inss(dados: dict[str, str], decisao: RetencaoImposto | None = None) -> None:
    """Validate and fill INSS retention fields."""
    valor_inss = dados["VALOR_INSS"]
    valor_total_nf = dados["VALOR_TOTAL_NF"]

    print(
        "[OS10] Validando INSS | "
        f"VALOR_INSS={valor_inss} | "
        f"VALOR_TOTAL_NF={valor_total_nf}"
    )

    if _is_zero_value(valor_inss):
        print("[OS10] INSS zerado. Lançando sem retenção.")

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("enter", presses=4, interval=0.2)
        _sleep(0.2)

        pyautogui.write("090", interval=0.03)
        pyautogui.press("enter")
        _sleep(0.2)

        pyautogui.press("up")
        _sleep(0.2)

        return

    print("[OS10] INSS encontrado. Calculando alíquota.")

    valor_total_nf_float = _to_float(valor_total_nf)
    valor_inss_float = _to_float(valor_inss)

    aliquota = 0.0
    if valor_total_nf_float > 0:
        aliquota = (valor_inss_float / valor_total_nf_float) * 100

    aliquota = round(aliquota, 1)
    aliquota_str = _format_decimal_br_1(aliquota)

    print(
        "[OS10] INSS calculado | "
        f"BASE={valor_total_nf} | "
        f"ALIQUOTA={aliquota_str} | "
        f"VALOR_INSS={valor_inss}"
    )

    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("VALOR_TOTAL_NF", valor_total_nf)
    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("ALIQUOTA_INSS", aliquota_str)
    pyautogui.press("enter")
    _sleep(0.2)

    _write_value("VALOR_INSS", valor_inss)
    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0,00", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("0,00", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.write("000", interval=0.03)
    _sleep(0.2)

    pyautogui.press("enter")
    _sleep(0.2)

    pyautogui.press("up")
    _sleep(0.2)


import time

import win32con
import win32gui


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _make_lparam(x: int, y: int) -> int:
    """Create LPARAM from client x/y coordinates."""
    return x | (y << 16)


def _find_window_startswith(title_prefix: str) -> int | None:
    """Find visible window whose title starts with given text."""
    found_hwnd: int | None = None

    def enum_window(hwnd: int, _: object) -> None:
        nonlocal found_hwnd

        if found_hwnd is not None:
            return

        if not win32gui.IsWindowVisible(hwnd):
            return

        title = win32gui.GetWindowText(hwnd).strip()

        if title.startswith(title_prefix):
            found_hwnd = hwnd

    win32gui.EnumWindows(enum_window, None)
    return found_hwnd


def _find_panel_by_size(
    parent_hwnd: int,
    panel_class: str,
    panel_width: int,
    panel_height: int,
) -> int | None:
    """Find a child panel by class and approximate size."""
    matches: list[int] = []

    def enum_child(hwnd: int, _: object) -> None:
        class_name = win32gui.GetClassName(hwnd)

        if class_name != panel_class:
            return

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        if width == panel_width and height == panel_height:
            matches.append(hwnd)

    win32gui.EnumChildWindows(parent_hwnd, enum_child, None)

    if not matches:
        return None

    return matches[0]


def clicar_icone_dentro_panel(
    parent_title: str,
    panel_class: str,
    panel_width: int,
    panel_height: int,
    offset_x: int,
    offset_y: int,
    label: str = "ícone dentro do panel",
) -> None:
    """Click an icon drawn inside a panel using panel-relative coordinates."""
    parent_hwnd = _find_window_startswith(parent_title)

    if not parent_hwnd:
        raise RuntimeError(f"Janela pai não encontrada: {parent_title}")

    panel_hwnd = _find_panel_by_size(
        parent_hwnd=parent_hwnd,
        panel_class=panel_class,
        panel_width=panel_width,
        panel_height=panel_height,
    )

    if not panel_hwnd:
        raise RuntimeError(
            f"Panel não encontrado | CLASS={panel_class} | "
            f"WIDTH={panel_width} | HEIGHT={panel_height}"
        )

    lparam = _make_lparam(offset_x, offset_y)

    print(
        f"[OS10] Clicando em {label} | "
        f"HWND={panel_hwnd} | "
        f"offset_x={offset_x} | offset_y={offset_y}"
    )

    win32gui.PostMessage(
        panel_hwnd,
        win32con.WM_LBUTTONDOWN,
        win32con.MK_LBUTTON,
        lparam,
    )
    _sleep(0.1)

    win32gui.PostMessage(
        panel_hwnd,
        win32con.WM_LBUTTONUP,
        0,
        lparam,
    )
    _sleep(0.5)


def clicar_botao_inss() -> None:
    """Click the lateral button inside Produtos panel."""
    clicar_icone_dentro_panel(
        parent_title="Nota Fiscal",
        panel_class="TPanel",
        panel_width=35,
        panel_height=270,
        offset_x=16,
        offset_y=30,
        label="botão INSS",
    )


def _find_child_by_class_instance(
    parent_hwnd: int,
    class_name: str,
    instance: int,
) -> int | None:
    """Find child control by class and instance."""
    matches: list[int] = []

    def enum_child(hwnd: int, _: object) -> None:
        if win32gui.GetClassName(hwnd) == class_name:
            matches.append(hwnd)

    win32gui.EnumChildWindows(parent_hwnd, enum_child, None)

    if len(matches) < instance:
        return None

    return matches[instance - 1]


def _processar_lancamento(nota: dict[str, Any]) -> None:
    """Open Agro flow, switch establishment, open Nota Fiscal and launch note."""
    dados = _dados_lancamento(nota)

    print(
        "[OS10] Preparando lançamento | "
        f"ESTAB={dados['ESTAB']} | "
        f"CNPJF_FORNECEDOR={dados['CNPJF_FORNECEDOR']} | "
        f"NUM_PED={dados['NUM_PED']} | "
        f"DTEMISSAO={dados['DTEMISSAO']} | "
        f"REGRA_NOTACONF={dados['REGRA_NOTACONF']}"
    )

    preparar_agro_para_lancamento(dados["ESTAB"])
    iniciar_nova_nota_fiscal()
    lancar_nota(
        dados,
        nota,
    )

    print(
        "[OS10] Nota Fiscal processada | "
        f"ESTAB={dados['ESTAB']} | "
        f"NUM_PED={dados['NUM_PED']} | "
        f"REGRA_NOTACONF={dados['REGRA_NOTACONF']}"
    )


def _dados_lancamento(nota: dict[str, Any]) -> dict[str, str]:
    """Normalize OS10 note data preserving database column names."""
    return {
        "ESTAB": _valor(nota, "ESTAB"),
        "CNPJ": _valor(nota, "CNPJ"),
        "TOMADOR_CNPJ": _valor(nota, "TOMADOR_CNPJ"),
        "REDUZIDO": _valor(nota, "REDUZIDO"),
        "SERIE": _valor(nota, "SERIE"),
        "NUM_PED": _valor(nota, "NUM_PED"),
        "PEDIDO": _valor(nota, "PEDIDO"),
        "CONCEITO": _valor(nota, "CONCEITO"),
        "FORNECEDOR": _valor(nota, "FORNECEDOR"),
        "CNPJ_PED": _valor(nota, "CNPJ_PED"),
        "CNPJF_FORNECEDOR": _valor(nota, "CNPJF_FORNECEDOR"),
        "EMITENTE_CNPJ": _valor(nota, "EMITENTE_CNPJ"),
        "IE_FORNECEDOR": _valor(nota, "IE_FORNECEDOR"),
        "COD_CONFIG": _valor(nota, "COD_CONFIG"),
        "CONFIG": _valor(nota, "CONFIG"),
        "DTEMISSAO": _valor(nota, "DTEMISSAO"),
        "VENCIMENTO": _valor(nota, "VENCIMENTO"),
        "VALORTOTAL": _valor(nota, "VALORTOTAL"),
        "VALOR_TOTAL_NF": _valor(nota, "VALOR_TOTAL_NF"),
        "USERID": _valor(nota, "USERID"),
        "PLACA": _valor(nota, "PLACA"),
        "DESCRICAO": _valor(nota, "DESCRICAO"),
        "TIPO_PROD": _valor(nota, "TIPO_PROD"),
        "ERROCHAVENFE": _valor(nota, "ERROCHAVENFE"),
        "REGRA_NOTACONF": _valor(nota, "REGRA_NOTACONF"),
        "CHAVCHAVENF": _valor(nota, "CHAVCHAVENF"),
        "TIPOPGTO": _valor(nota, "TIPOPGTO"),
        "CHAVEBOLETO": _valor(nota, "CHAVEBOLETO"),
        "BANCO": _valor(nota, "BANCO"),
        "AGENCIA": _valor(nota, "AGENCIA"),
        "CONTA": _valor(nota, "CONTA"),
        "PIX": _valor(nota, "PIX"),
        "NOTATERC": _valor(nota, "NOTATERC"),
        "ARQUIVO_XML": _valor(nota, "ARQUIVO_XML"),
        "DESC_INCOND": _valor(nota, "DESC_INCOND"),
        "DESC_COND": _valor(nota, "DESC_COND"),
        "VALOR_LIQUIDO": _valor(nota, "VALOR_LIQUIDO"),
        "VALOR_RETENCAO": _valor(nota, "VALOR_RETENCAO"),
        "PISBASE": _valor(nota, "PISBASE"),
        "COFINSBASE": _valor(nota, "COFINSBASE"),
        "ALIQPIS": _valor(nota, "ALIQPIS"),
        "ALIQCOFINS": _valor(nota, "ALIQCOFINS"),
        "VALOR_PIS": _valor(nota, "VALOR_PIS"),
        "VALOR_COFINS": _valor(nota, "VALOR_COFINS"),
        "VALOR_IRRF": _valor(nota, "VALOR_IRRF"),
        "VALOR_CSLL": _valor(nota, "VALOR_CSLL"),
        "VALOR_INSS": _valor(nota, "VALOR_INSS"),
        "BCISSQN": _valor(nota, "BCISSQN"),
        "ALIQISSQN": _valor(nota, "ALIQISSQN"),
        "VALOR_ISSQN": _valor(nota, "VALOR_ISSQN"),
        "RETPISCOFINS": _valor(nota, "RETPISCOFINS"),
        "RETISSQN": _valor(nota, "RETISSQN"),
        "LOCALNF": _valor(nota, "LOCALNF"),
        "NUMERO_NF": _valor(nota, "NUMERO_NF"),
        "VAL_VALOR": _valor(nota, "VAL_VALOR"),
        "VAL_CHAVE_BOLETO": _valor(nota, "VAL_CHAVE_BOLETO"),
        "VAL_RET_MES": _valor(nota, "VAL_RET_MES"),
        "VAL_CNPJ_DEST": _valor(nota, "VAL_CNPJ_DEST"),
        "VAL_CNPJ_FORNEC": _valor(nota, "VAL_CNPJ_FORNEC"),
        "VAL_SERVICO_ITEM": _valor(nota, "VAL_SERVICO_ITEM"),
        "SERVICO_CODIGO": _valor(nota, "SERVICO_CODIGO"),
        "ITEM_DESC": _valor(nota, "ITEM_DESC"),
        "ITEM": _valor(nota, "ITEM"),
    }


def montar_linha_relatorio_final(
    nota: dict[str, Any],
    mensagem: str,
) -> dict[str, Any]:
    """Build OS10 final report row."""
    dados = _dados_lancamento(nota)

    return {
        "Estab": dados["ESTAB"],
        "CNPJ Fornecedor": dados["CNPJF_FORNECEDOR"],
        "NumPedido": dados["NUM_PED"],
        "Data_Emissao": dados["DTEMISSAO"],
        "Mensagem": mensagem,
    }


def montar_linha_relatorio_erro(
    nota: dict[str, Any],
    mensagem: str,
) -> dict[str, Any]:
    """Build OS10 error report row."""
    dados = _dados_lancamento(nota)

    return {
        "Estabelecimento": dados["ESTAB"],
        "Número da nota": dados["NUMERO_NF"],
        "Pedido": dados["NUM_PED"],
        "Valor": dados["VALOR_TOTAL_NF"],
        "Data Emissao": dados["DTEMISSAO"],
        "CNPJ Fornecedor": dados["CNPJF_FORNECEDOR"],
        "Mensagem": mensagem,
    }


def preparar_agro_para_lancamento(estab: str) -> None:
    """Prepare Agro until Nota Fiscal screen."""
    trocar_estabelecimento_agro(estab)
    abrir_tela_nota_fiscal()


def trocar_estabelecimento_agro(estab: str) -> None:
    """Switch establishment in Agro."""
    if not estab:
        raise RuntimeError("ESTAB não informado para troca de estabelecimento.")

    print("[OS10] Troca de estabelecimento.")
    print(f"[OS10] Enviando variável ESTAB: {estab}")

    if not switch_establishment(estab, main_title="AGRO-"):
        raise RuntimeError(f"Falha ao trocar para o estabelecimento {estab}.")

    # Aguarda o Agro terminar a troca de estabelecimento antes de enviar ALT+N.
    _sleep(3)
    print(f"[OS10] Estabelecimento alterado para {estab}.")


def abrir_tela_nota_fiscal() -> None:
    """Open Nota Fiscal list screen ensuring Agro focus."""
    print("[OS10] Caminho: abrir tela Nota Fiscal.")

    hwnd_agro = _find_window_startswith("AGRO-")

    if not hwnd_agro:
        raise RuntimeError(
            "Janela principal do Agro não encontrada antes do ALT+N."
        )

    print("[OS10] Focando Agro antes do ALT+N.")

    try:
        win32gui.SetForegroundWindow(hwnd_agro)
    except Exception:
        pass

    _sleep(2)

    print("[OS10] Comando: ALT + N")
    pyautogui.hotkey("alt", "n")
    _sleep(2)

    print("[OS10] Comando: ENTER")
    pyautogui.press("enter")
    _sleep(3)

    print("[OS10] Aguardando tela: Filtrar NF - Cabeçalho")
    if not wait_window_startswith(
        "Filtrar NF - Cabeçalho",
        timeout_seconds=15,
    ):
        raise RuntimeError(
            "Tela 'Filtrar NF - Cabeçalho' não apareceu após ALT+N."
        )

    print("[OS10] Tela encontrada: Filtrar NF - Cabeçalho")

    print("[OS10] Comando: ALT + V")
    pyautogui.hotkey("alt", "v")
    _sleep(3)

    print("[OS10] Aguardando tela: Nota Fiscal")
    if not wait_window_startswith(
        "Nota Fiscal",
        timeout_seconds=15,
    ):
        raise RuntimeError("Tela 'Nota Fiscal' não carregou.")

    _sleep(1)
    print("[OS10] Tela carregada: Nota Fiscal")


def iniciar_nova_nota_fiscal() -> None:
    """Start a new Nota Fiscal with CTRL + INSERT."""
    print("[OS10] Caminho: iniciar nova Nota Fiscal.")

    _sleep(1)

    print("[OS10] Comando: CTRL + INSERT")
    pyautogui.hotkey("ctrl", "insert")
    _sleep(3)

    print("[OS10] Aguardando tela: Nota Fiscal após CTRL + INSERT")
    if not wait_window_startswith("Nota Fiscal", timeout_seconds=15):
        raise RuntimeError("Tela 'Nota Fiscal' não carregou após CTRL + INSERT.")

    _sleep(1)
    print("[OS10] Nova Nota Fiscal aberta.")




# ============================================================
# ACERTO FINANCEIRO / PAGAMENTO
# Integrado a partir do fluxo enviado para OS14.
# ============================================================


def normalizar_titulo(titulo: str) -> str:
    titulo = unicodedata.normalize("NFKD", titulo)
    titulo = "".join(c for c in titulo if not unicodedata.combining(c))
    return titulo.lower().strip()


def confirmar_atencao_se_existir(timeout: int = 3) -> bool:
    """
    Confirma com ENTER qualquer popup de Atenção, Erro ou Aviso.

    Mantém o nome da função para não alterar o restante da lógica do robô.
    """
    deadline = time.time() + timeout

    while time.time() < deadline:
        for janela in gw.getAllWindows():
            titulo = str(janela.title or "").strip()
            titulo_normalizado = normalizar_titulo(titulo)

            if not titulo_normalizado:
                continue

            if (
                "atencao" not in titulo_normalizado
                and "erro" not in titulo_normalizado
                and "aviso" not in titulo_normalizado
            ):
                continue

            print(
                "[OS10] Popup encontrado. Confirmando com ENTER | "
                f"TITULO={titulo}"
            )

            try:
                if janela.isMinimized:
                    janela.restore()
                    time.sleep(0.3)

                janela.activate()
                time.sleep(0.3)

            except Exception:
                try:
                    hwnd = getattr(janela, "_hWnd", None)

                    if hwnd:
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.3)
                except Exception:
                    pass

            pyautogui.press("enter")
            time.sleep(1)
            return True

        time.sleep(0.2)

    return False




def get_process_session_id(pid: int) -> int | None:
    session_id = ctypes.c_ulong()

    success = ctypes.windll.kernel32.ProcessIdToSessionId(
        ctypes.c_ulong(pid),
        ctypes.byref(session_id),
    )

    return int(session_id.value) if success else None


def kill_agro_process(process_name: str = "Agro3C.exe") -> int:
    """Finaliza somente Agro da sessão atual."""
    killed = 0
    current_session_id = get_process_session_id(os.getpid())

    if current_session_id is None:
        raise RuntimeError("Não foi possível identificar a sessão atual do Python.")

    for process in psutil.process_iter(["pid", "name"]):
        try:
            name = process.info.get("name")
            pid = process.info.get("pid")

            if not name or not pid:
                continue

            if name.lower() != process_name.lower():
                continue

            if get_process_session_id(pid) != current_session_id:
                continue

            process.kill()
            process.wait(timeout=5)
            killed += 1

            print(f"[OS10] Processo finalizado: {name} PID={pid}")

        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            print(f"[OS10] Sem permissão para finalizar {process_name}")
        except psutil.TimeoutExpired:
            print(f"[OS10] Timeout ao finalizar {process_name}")

    if killed:
        _sleep(2)

    return killed


def start_agro(agro_exe: str) -> subprocess.Popen:
    """Abre novamente o Agro."""
    agro_path = Path(agro_exe)

    if not agro_path.exists():
        raise FileNotFoundError(f"Executável do Agro não encontrado: {agro_exe}")

    return subprocess.Popen(
        [str(agro_path)],
        cwd=str(agro_path.parent),
    )


def _aguardar_selecao_estabelecimento(timeout: int = 30) -> int:
    """Aguarda a tela de seleção de estabelecimento após o login."""
    print(
        "[OS10] Aguardando tela de seleção de estabelecimento | "
        "TITLE=Seleção de Estabelecimento para Trabalho | CLASS=TfmSelEmp"
    )

    deadline = time.time() + timeout

    while time.time() < deadline:
        hwnd = win32gui.FindWindow(
            "TfmSelEmp",
            None,
        )

        if hwnd and win32gui.IsWindowVisible(hwnd):
            return hwnd

        hwnd = _find_window_startswith(
            "Seleção de Estabelecimento para Trabalho"
        )

        if hwnd:
            return hwnd

        _sleep(0.5)

    raise RuntimeError(
        "Tela 'Seleção de Estabelecimento para Trabalho' não apareceu após o login."
    )


def _confirmar_atencao_exata(timeout: int = 2) -> bool:
    """Confirma somente Title=Atenção / Class=#32770."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        hwnd = win32gui.FindWindow(
            "#32770",
            "Atenção",
        )

        if hwnd and win32gui.IsWindowVisible(hwnd):
            print(
                "[OS10] Tela Atenção encontrada durante inicialização do Agro."
            )

            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass

            _sleep(0.3)
            pyautogui.press("enter")
            _sleep(1)
            return True

        _sleep(0.2)

    return False


def _preparar_agro_apos_login() -> None:
    """Executa o caminho correto: login -> estabelecimento -> Agro principal."""
    print("[OS10] Verificando tela Atenção após login.")
    _confirmar_atencao_exata(timeout=3)

    hwnd_estab = _aguardar_selecao_estabelecimento(timeout=30)

    print(
        "[OS10] Tela 'Seleção de Estabelecimento para Trabalho' encontrada."
    )

    try:
        win32gui.SetForegroundWindow(hwnd_estab)
    except Exception:
        pass

    _sleep(0.8)

    print("[OS10] Seleção de estabelecimento: ENTER")
    pyautogui.press("enter")
    _sleep(1)

    # Algumas versões do Agro mantêm a seleção aberta após o primeiro ENTER.
    # Nesse caso, confirma novamente.
    if win32gui.IsWindow(hwnd_estab) and win32gui.IsWindowVisible(hwnd_estab):
        print("[OS10] Seleção de estabelecimento ainda aberta. ENTER novamente.")
        pyautogui.press("enter")
        _sleep(1)

    _confirmar_atencao_exata(timeout=2)

    print(
        "[OS10] Aguardando tela principal do Agro | prefixo=AGRO-"
    )

    timeout = time.time() + 60

    while time.time() < timeout:
        hwnd_agro = _find_window_startswith("AGRO-")

        if hwnd_agro:
            try:
                win32gui.SetForegroundWindow(hwnd_agro)
            except Exception:
                pass

            print(
                "[OS10] Sistema aberto com sucesso | "
                f"prefixo=AGRO- | titulo={win32gui.GetWindowText(hwnd_agro).strip()}"
            )
            return

        _sleep(1)

    raise RuntimeError(
        "Agro não carregou após login e seleção de estabelecimento."
    )


def abrir_agro_completo() -> None:
    """Abre o Agro pelo mesmo caminho completo usado no início."""
    if not AGRO_EXE:
        raise RuntimeError("AGRO_EXE não configurado.")

    print("[OS10] Inicializando Agro.")
    start_agro(AGRO_EXE)

    print("[OS10] Aguardando tela de login.")
    _sleep(5)

    print("[OS10] Executando login.")
    login_agro()
    print("[OS10] Login executado.")

    _preparar_agro_apos_login()


def reiniciar_agro() -> None:
    """Reinicia Agro após erro crítico realizando login novamente."""

    print("[OS10] Reiniciando Agro após erro crítico.")

    killed = kill_agro_process()

    print(f"[OS10] Processos Agro finalizados: {killed}")

    _sleep(3)

    abrir_agro_completo()

    _sleep(3)

    print("[OS10] Restart completo do Agro concluído.")


def tratar_atencao_pos_alt_b(nota: dict[str, Any]) -> None:
    """
    Trata somente Atenção (#32770) que surgir após ALT+B.

    Se não existir a janela Atenção, não altera foco, não fecha telas e não
    reinicia o Agro. O fluxo chamador simplesmente continua para CTRL+S.
    """
    deadline = time.time() + 3
    hwnd: int | None = None

    while time.time() < deadline:
        candidato = win32gui.FindWindow(
            "#32770",
            "Atenção",
        )

        if candidato and win32gui.IsWindowVisible(candidato):
            hwnd = candidato
            break

        _sleep(0.2)

    if not hwnd:
        print(
            "[OS10] Nenhuma tela Atenção após ALT+B. "
            "Não reiniciando Agro. Continuando para CTRL+S."
        )
        return

    print("[OS10] Tela Atenção encontrada após ALT+B.")

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    _sleep(0.5)

    screenshot_path = tirar_print_erro(nota)

    print(
        "[OS10] Print da Atenção salvo: "
        f"{screenshot_path}"
    )

    print("[OS10] Confirmando Atenção com ENTER.")
    pyautogui.press("enter")
    _sleep(1)

    # Não fecha telas transacionais. O processo inteiro do Agro será reiniciado.
    reiniciar_agro()

    # A nota atual terminou aqui. O executar_lancamento() captura a exceção
    # e usa continue para iniciar a próxima linha.
    raise RuntimeError(
        "Tela Atenção apareceu após ALT+B. Agro reiniciado. Próxima linha."
    )


def buscar_janela_por_titulo(titulo: str, timeout: int = 10):
    titulo_normalizado = normalizar_titulo(titulo)

    for _ in range(timeout):
        for janela in gw.getAllWindows():
            if titulo_normalizado in normalizar_titulo(janela.title):
                return janela
        time.sleep(1)

    return None


def focar_janela_por_titulo(titulo: str, timeout: int = 10) -> bool:
    """Focus a visible window by partial title without depending on OS14."""
    janela = buscar_janela_por_titulo(titulo, timeout=timeout)

    if janela is None:
        print(f"[OS10] Janela não encontrada para foco: {titulo}")
        return False

    try:
        if janela.isMinimized:
            janela.restore()
            time.sleep(0.3)

        janela.activate()
        time.sleep(0.3)
        return True

    except Exception as exc:
        print(
            f"[OS10] Falha ao ativar janela '{titulo}' via pygetwindow: {exc}"
        )

        try:
            hwnd = getattr(janela, "_hWnd", None)
            if hwnd:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)
                return True
        except Exception as exc2:
            print(
                f"[OS10] Falha ao focar janela '{titulo}' via Win32: {exc2}"
            )

    return False


def validar_tela_valores_pendentes(
    pedido: dict,
    timeout: int = 3,
) -> bool:
    """
    Safe OS10-local validation for the optional 'Valores Pendentes' screen.

    The original implementation lived in robot_OS14 and was not supplied with
    this standalone OS10 project. To avoid a hidden/incorrect automation, this
    local version allows the flow to continue when the screen does not appear
    and stops with an explicit error if it does appear.
    """
    _ = pedido

    janela = buscar_janela_por_titulo(
        "Valores Pendentes",
        timeout=timeout,
    )

    if janela is None:
        print("[OS10] Tela 'Valores Pendentes' não apareceu. Seguindo fluxo.")
        return False

    try:
        if janela.isMinimized:
            janela.restore()
            time.sleep(0.3)
        janela.activate()
        time.sleep(0.3)
    except Exception:
        pass

    raise RuntimeError(
        "Tela 'Valores Pendentes' apareceu, mas o tratamento original dessa "
        "tela pertence ao robot_OS14 e não existe neste projeto OS10. "
        "O fluxo foi interrompido para evitar preenchimento incorreto."
    )


def tela_pagamento_duplicatas_aberta(timeout: int = 10) -> bool:
    return (
        buscar_janela_por_titulo(
            "Pagamento com Duplicatas",
            timeout=timeout,
        )
        is not None
    )


def pressionar_alt_a() -> None:
    pyautogui.hotkey("alt", "a")


def clicar_regiao_pagamento() -> None:
    janela = buscar_janela_por_titulo(
        "Pagamento com Duplicatas",
        timeout=10,
    )

    if janela is None:
        raise RuntimeError("Tela 'Pagamento com Duplicatas' não encontrada.")

    janela_pywinauto = Desktop(backend="win32").window(handle=janela._hWnd)
    janela_pywinauto.wait("exists", timeout=10)

    grids = janela_pywinauto.children(class_name="TVsStringGrid")
    total_grids = len(grids)

    print(f"[OS10] Total de grids TVsStringGrid encontrados: {total_grids}")

    if total_grids == 0:
        raise RuntimeError(
            "Grid de pagamento não encontrado. ClassName=TVsStringGrid"
        )

    if total_grids > 1:
        raise RuntimeError(
            "Mais de um grid encontrado na tela 'Pagamento com Duplicatas'. "
            f"Total encontrado: {total_grids}. "
            "Processo bloqueado para evitar preenchimento no grid errado."
        )

    grids[0].click_input(coords=(80, 27))
    time.sleep(1)


def navegar_direita(vezes: int) -> None:
    for _ in range(vezes):
        pyautogui.press("right")
        time.sleep(0.10)


def preencher_campo(valor: str, descricao: str = "campo") -> None:
    valor = str(valor or "").strip()

    if not valor:
        raise RuntimeError(f"Valor não informado para {descricao}.")

    print(f"[OS10] Preenchendo {descricao}: {valor}")

    pyautogui.write(valor, interval=0.03)
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(1)

    atencao_confirmada = confirmar_atencao_se_existir(timeout=2)

    if atencao_confirmada:
        print(
            f"[OS10] Tela Atenção apareceu após preencher {descricao}. "
            "Aviso confirmado."
        )
        focar_janela_por_titulo("Pagamento com Duplicatas", timeout=10)
        time.sleep(0.5)
        return

    print(f"[OS10] {descricao} preenchido sem tela de Atenção.")


def _montar_pedido_financeiro(dados: dict[str, str]) -> dict[str, str]:
    """Create a dict compatible with the supplied OS14 financial helpers."""
    pedido = dict(dados)

    for chave, valor in dados.items():
        pedido.setdefault(chave.lower(), valor)

    return pedido


def _linha_digitavel_ja_cadastrada(timeout: int = 3) -> bool:
    """
    Detecta o aviso específico de linha digitável já cadastrada.

    Quando encontrado:
    - foca a janela Atenção;
    - confirma com ENTER;
    - retorna True para o fluxo encerrar a nota atual.
    """
    deadline = time.time() + timeout

    while time.time() < deadline:
        tela_atencao = win32gui.FindWindow(
            "#32770",
            "Atenção",
        )

        if tela_atencao and win32gui.IsWindowVisible(tela_atencao):
            texto_hwnd = _find_child_by_class_instance(
                parent_hwnd=tela_atencao,
                class_name="Static",
                instance=2,
            )

            texto = ""

            if texto_hwnd:
                texto = win32gui.GetWindowText(
                    texto_hwnd
                ).strip()

            texto_normalizado = normalizar_titulo(texto)

            if (
                texto_normalizado.startswith("a linha digitavel")
                and "ja esta cadastrada em outro titulo" in texto_normalizado
            ):
                print(
                    "[OS10] Linha Digitável já cadastrada em outro título. "
                    "Fechando Atenção com ENTER e pulando para a próxima nota."
                )

                try:
                    win32gui.SetForegroundWindow(
                        tela_atencao
                    )
                except Exception:
                    pass

                _sleep(0.3)

                pyautogui.press(
                    "enter"
                )

                _sleep(0.8)

                return True

            return False

        _sleep(0.2)

    return False


def preencher_boleto(pedido: dict) -> None:
    navegar_direita(13)
    time.sleep(0.5)

    pyautogui.press("enter")
    time.sleep(0.5)

    chave_boleto = str(
        pedido["chaveboleto"] or ""
    ).strip()

    if not chave_boleto:
        raise RuntimeError(
            "Chave do boleto não informada."
        )

    print(
        f"[OS10] Preenchendo chave do boleto: {chave_boleto}"
    )

    pyautogui.write(
        chave_boleto,
        interval=0.03,
    )

    time.sleep(0.5)

    pyautogui.press(
        "enter"
    )

    time.sleep(0.8)

    if _linha_digitavel_ja_cadastrada(
        timeout=3,
    ):
        raise RuntimeError(
            "Linha Digitável já cadastrada em outro título. "
            "Nota atual encerrada para seguir para a próxima."
        )

    if confirmar_atencao_se_existir(
        timeout=2
    ):
        print(
            "[OS10] Atenção/Erro/Aviso após preencher "
            "a chave do boleto confirmado com ENTER."
        )

        focar_janela_por_titulo(
            "Pagamento com Duplicatas",
            timeout=10,
        )

        time.sleep(0.5)

    tratar_atencao_pagamento()

def preencher_deposito(pedido: dict) -> None:
    navegar_direita(14)
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    confirmar_atencao_se_existir(timeout=2)
    preencher_campo(pedido["banco"], descricao="banco")
    pyautogui.press("enter")
    preencher_campo(pedido["agencia"], descricao="agência")
    preencher_campo(pedido["conta"], descricao="conta")
    tratar_atencao_pagamento()


def preencher_pix(pedido: dict) -> None:
    navegar_direita(30)
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    preencher_campo("3", descricao="tipo de PIX")
    preencher_campo(pedido["pix"], descricao="chave PIX")
    tratar_atencao_pagamento()



def preencher_referencia_atencao_pagamento(
    dados: dict[str, str],
) -> bool:
    """
    Trata Atenção após CTRL+S da tela Pagamento com Duplicatas.

    Preenche o campo equivalente ao:
    /Window[3]/Pane/Edit[8]

    Valor:
    NUMERO_NF-NUM_PED

    Depois confirma com ENTER.
    """

    hwnd = win32gui.FindWindow(
        "#32770",
        "Atenção",
    )

    if not hwnd or not win32gui.IsWindowVisible(hwnd):
        return False

    print(
        "[OS10] Atenção encontrada após CTRL+S da duplicata."
    )

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    _sleep(0.5)

    campo = _find_child_by_class_instance(
        parent_hwnd=hwnd,
        class_name="Edit",
        instance=8,
    )

    if not campo:
        raise RuntimeError(
            "Campo Edit[8] não encontrado na tela Atenção."
        )

    referencia = (
        f"{dados.get('NUMERO_NF', '')}"
        "-"
        f"{dados.get('NUM_PED', '')}"
    )

    print(
        "[OS10] Preenchendo referência Atenção: "
        f"{referencia}"
    )

    try:
        win32gui.SetForegroundWindow(campo)
    except Exception:
        pass

    _sleep(0.3)

    pyautogui.click()
    pyautogui.hotkey("ctrl", "a")

    pyautogui.write(
        referencia,
        interval=0.03,
    )

    _sleep(0.5)

    print("[OS10] Confirmando referência Atenção com ENTER.")
    pyautogui.press("enter")

    _sleep(1)

    return True


def salvar_pagamento(
    dados: dict[str, str],
) -> None:
    """Send CTRL+S on Pagamento com Duplicatas and handle Atenção."""

    print("[OS10] Pagamento com Duplicatas: primeiro CTRL + S")

    pyautogui.hotkey("ctrl", "s")
    time.sleep(1)

    if preencher_referencia_atencao_pagamento(dados):

        print(
            "[OS10] Referência preenchida. "
            "Executando CTRL+S novamente."
        )

        pyautogui.hotkey("ctrl", "s")
        time.sleep(1)

        confirmar_atencao_se_existir(timeout=2)

    print(
        "[OS10] Primeiro CTRL + S enviado. "
        "Aguardando a tela Acerto Financeiro para o segundo CTRL + S."
    )



def _janela_visivel_por_classe(class_name: str) -> int | None:
    """Return a visible top-level window handle by class name."""
    hwnd = win32gui.FindWindow(class_name, None)

    if hwnd and win32gui.IsWindowVisible(hwnd):
        return hwnd

    return None


def _configuracao_e_504(dados: dict[str, str]) -> bool:
    """
    Identifica configuração 504.

    REGRA_NOTACONF é a referência principal do OS10.
    """
    for campo in ("REGRA_NOTACONF", "COD_CONFIG", "CONFIG"):
        valor = str(dados.get(campo, "") or "").strip()

        if not valor:
            continue

        print(
            "[OS10] Validando configuração | "
            f"{campo}={valor}"
        )

        valor_normalizado = (
            valor
            .replace(" ", "")
            .replace("-", "")
            .upper()
        )

        if valor_normalizado == "504":
            print("[OS10] Configuração 504 confirmada.")
            return True

        try:
            if float(valor_normalizado.replace(",", ".")) == 504.0:
                print("[OS10] Configuração 504 confirmada.")
                return True
        except ValueError:
            pass

    print("[OS10] Configuração diferente de 504.")
    return False


def _maximizar_janela(hwnd: int, descricao: str) -> None:
    """Maximize and focus a top-level window."""
    if not hwnd:
        raise RuntimeError(f"Janela invalida para maximizar: {descricao}")

    print(f"[OS10] Maximizando tela: {descricao}")
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    _sleep(0.5)

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    _sleep(0.5)


def _clicar_primeiro_botao_toolbar_frota(hwnd: int) -> None:
    """Click the AE-equivalent ToolBar/Button[1] inside TFrGerarNFFrota."""
    _maximizar_janela(hwnd, "TFrGerarNFFrota")

    try:
        janela = Desktop(backend="uia").window(handle=hwnd)
        janela.wait("exists visible enabled", timeout=10)

        # Equivalent relative path inside TFrGerarNFFrota:
        # Window[1]/Pane[1]/Pane[1]/Pane[1]/Group[1]/Pane[2]/ToolBar[1]/Button[1]
        try:
            nivel = janela.children(control_type="Window")[0]
            nivel = nivel.children(control_type="Pane")[0]
            nivel = nivel.children(control_type="Pane")[0]
            nivel = nivel.children(control_type="Pane")[0]
            nivel = nivel.children(control_type="Group")[0]
            nivel = nivel.children(control_type="Pane")[1]
            nivel = nivel.children(control_type="ToolBar")[0]
            botao = nivel.children(control_type="Button")[0]

            print("[OS10] Clicando Button[1] pelo caminho UIA equivalente ao ClickWait.")
            botao.click_input()
            _sleep(1)
            return
        except (IndexError, RuntimeError):
            print(
                "[OS10] Caminho UIA exato nao localizado. "
                "Tentando localizar o primeiro Button dentro de uma ToolBar."
            )

        toolbars = janela.descendants(control_type="ToolBar")
        print(f"[OS10] ToolBars encontrados em TFrGerarNFFrota: {len(toolbars)}")

        for indice_toolbar, toolbar in enumerate(toolbars, start=1):
            botoes = toolbar.descendants(control_type="Button")
            if not botoes:
                continue

            print(
                "[OS10] Clicando no primeiro botao da ToolBar | "
                f"toolbar={indice_toolbar} | button=1"
            )
            botoes[0].click_input()
            _sleep(1)
            return

    except Exception as exc:
        raise RuntimeError(
            "Falha ao clicar no Button[1] da ToolBar em TFrGerarNFFrota: "
            f"{exc}"
        ) from exc

    raise RuntimeError(
        "Nenhum Button[1] acessivel foi encontrado em uma ToolBar de TFrGerarNFFrota."
    )


def _ler_valor_campo_atual() -> str:
    """Copy the currently focused field/cell and return its text."""
    _set_clipboard_text("")
    _sleep(0.1)
    pyautogui.hotkey("ctrl", "c")
    _sleep(0.3)
    return _get_clipboard_text().strip()





def tratar_validacao_acerto_financeiro(
    nota: dict[str, Any],
) -> None:
    """
    Trata:
    Title: Validação do Acerto Financeiro
    Class: #32770

    Fluxo:
    - Localiza a validação.
    - Força foco nela.
    - Confirma que ela é a janela ativa.
    - Confirma o popup.
    - Reinicia o Agro.
    """

    hwnd_validacao = win32gui.FindWindow(
        "#32770",
        "Validação do Acerto Financeiro",
    )

    if not hwnd_validacao or not win32gui.IsWindowVisible(hwnd_validacao):
        print("[OS10] Validação do Acerto Financeiro não apareceu.")
        return False

    print("[OS10] Tela Validação do Acerto Financeiro encontrada.")

    if win32gui.IsIconic(hwnd_validacao):
        win32gui.ShowWindow(
            hwnd_validacao,
            win32con.SW_RESTORE,
        )
        _sleep(0.5)

    foco_confirmado = False

    print("[OS10] Focando Validação do Acerto Financeiro.")

    for tentativa in range(1, 6):
        try:
            win32gui.BringWindowToTop(hwnd_validacao)
            win32gui.SetForegroundWindow(hwnd_validacao)
        except Exception as exc:
            print(
                f"[OS10] Erro ao focar validação | tentativa={tentativa} | {exc}"
            )

        _sleep(0.5)

        if win32gui.GetForegroundWindow() == hwnd_validacao:
            foco_confirmado = True
            break

    if not foco_confirmado:
        raise RuntimeError(
            "Não foi possível focar a tela Validação do Acerto Financeiro."
        )

    print("[OS10] Validação do Acerto Financeiro está focada.")

    screenshot_path = tirar_print_erro(nota)
    print(
        "[OS10] Screenshot Validação Acerto Financeiro: "
        f"{screenshot_path}"
    )

    pyautogui.press("enter")
    _sleep(2)

    print("[OS10] Reiniciando Agro após Validação do Acerto Financeiro.")

    reiniciar_agro()

    raise RuntimeError(
        "Validação do Acerto Financeiro apareceu. Agro reiniciado."
    )


def tratar_atencao_pagamento() -> None:
    """Confirma tela Atenção após informar forma de pagamento."""

    hwnd = win32gui.FindWindow("#32770", "Atenção")

    if hwnd and win32gui.IsWindowVisible(hwnd):
        print("[OS10] Atenção após forma de pagamento. Confirmando ENTER.")

        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

        _sleep(0.5)
        pyautogui.press("enter")
        _sleep(1)


def _executar_fluxo_config_504(dados: dict[str, str]) -> None:
    """Execute the special fleet/vehicle flow used by configuration 504."""
    placa = str(dados.get("PLACA", "") or "").strip()
    numero_pedido = str(dados.get("NUM_PED", "") or "").strip()

    if not placa:
        raise RuntimeError("PLACA nao informada para a configuracao 504.")

    if not numero_pedido:
        raise RuntimeError("NUM_PED nao informado para a configuracao 504.")

    print("[OS10] Configuracao 504 detectada. Aguardando TFrGerarNFFrota.")
    tela_frota = _aguardar_janela_classe("TFrGerarNFFrota", timeout=15)

    if not tela_frota:
        raise RuntimeError(
            "Tela TFrGerarNFFrota nao apareceu apos o TAB do LOCALNF."
        )

    # Foca somente a janela TFrGerarNFFrota.
    # Não usa set_focus() em controles internos para não mudar
    # a posição de navegação que o Agro deixou selecionada.
    print("[OS10] Focando TFrGerarNFFrota.")

    try:
        win32gui.ShowWindow(
            tela_frota,
            win32con.SW_MAXIMIZE,
        )
        _sleep(0.5)

        win32gui.SetForegroundWindow(tela_frota)

    except Exception as exc:
        raise RuntimeError(
            f"Nao foi possivel focar TFrGerarNFFrota: {exc}"
        ) from exc

    _sleep(1)

    janela_ativa = win32gui.GetForegroundWindow()
    classe_ativa = win32gui.GetClassName(janela_ativa)

    if classe_ativa != "TFrGerarNFFrota":
        raise RuntimeError(
            "TFrGerarNFFrota foi encontrada, mas nao ficou ativa. "
            f"CLASS ativa={classe_ativa}"
        )

    # Sequência solicitada assim que TFrGerarNFFrota estiver focada.
    print("[OS10] TFrGerarNFFrota: SHIFT + TAB 1x")

    pyautogui.hotkey(
        "shift",
        "tab",
    )

    _sleep(1)

    print("[OS10] TFrGerarNFFrota: RIGHT 3x")
    pyautogui.press(
        "right",
        presses=3,
        interval=0.2,
    )
    _sleep(0.5)

    print("[OS10] TFrGerarNFFrota: digitando 2")
    pyautogui.write(
        "2",
        interval=0.03,
    )
    _sleep(0.5)

    print("[OS10] TFrGerarNFFrota: TAB")
    pyautogui.press("tab")
    _sleep(0.5)

    print("[OS10] TFrGerarNFFrota: ALT + P")
    pyautogui.hotkey("alt", "p")
    _sleep(1)

    # The AutomationEdge selector supplied by the process points to:
    # /Window[5]/Window[1]/Pane/Pane/Pane/Group[1]/Pane[2]/ToolBar/Button[1]
    # We resolve the equivalent accessible ToolBar/Button through UIA.
    tela_frota = _aguardar_janela_classe("TFrGerarNFFrota", timeout=10)
    if not tela_frota:
        raise RuntimeError("TFrGerarNFFrota nao encontrada antes do clique na ToolBar.")

    _clicar_primeiro_botao_toolbar_frota(tela_frota)

    print("[OS10] Aguardando TFPlacaVeiculos.")
    tela_placa = _aguardar_janela_classe("TFPlacaVeiculos", timeout=15)

    if not tela_placa:
        raise RuntimeError("Tela TFPlacaVeiculos nao apareceu.")

    try:
        win32gui.SetForegroundWindow(tela_placa)
    except Exception:
        pass

    _sleep(0.5)

    print("[OS10] TFPlacaVeiculos: TAB")
    pyautogui.press("tab")
    _sleep(0.3)

    print(f"[OS10] TFPlacaVeiculos: informando PLACA={placa}")
    pyautogui.write(placa, interval=0.03)
    _sleep(0.3)

    print("[OS10] TFPlacaVeiculos: ENTER")
    pyautogui.press("enter")
    _sleep(0.8)

    print("[OS10] TFPlacaVeiculos: TAB 4x")
    pyautogui.press("tab", presses=4, interval=0.2)
    _sleep(0.5)

    print("[OS10] TFPlacaVeiculos: RIGHT 10x")
    pyautogui.press("right", presses=10, interval=0.1)
    _sleep(0.3)

    motorista = _ler_valor_campo_atual()
    print(f"[OS10] Motorista atual: {motorista!r}")

    if not motorista:
        print("[OS10] Motorista vazio. Informando motorista 1.")
        pyautogui.write("1", interval=0.03)
        _sleep(0.3)
    else:
        print("[OS10] Motorista ja informado. Mantendo valor atual.")

    print("[OS10] TFPlacaVeiculos: ALT + S")
    pyautogui.hotkey("alt", "s")
    _sleep(1)

    print("[OS10] Aguardando retorno para Nota Fiscal após ALT + S.")

    tela_nota = _aguardar_janela_classe("TFNfCab", timeout=15)
    if not tela_nota:
        raise RuntimeError(
            "Tela Nota Fiscal não retornou após ALT + S em TFPlacaVeiculos."
        )

    try:
        win32gui.SetForegroundWindow(tela_nota)
    except Exception:
        pass

    _sleep(1)

    print("[OS10] Retornou para Nota Fiscal após fluxo Frota.")



def _buscar_janela_advertencias_nota() -> int | None:
    """Return the visible Nota Fiscal warnings/inconsistencies window."""
    encontrada: int | None = None

    def enum_window(hwnd: int, _: object) -> None:
        nonlocal encontrada

        if encontrada is not None:
            return

        if not win32gui.IsWindowVisible(hwnd):
            return

        titulo = win32gui.GetWindowText(hwnd).strip()
        titulo_normalizado = normalizar_titulo(titulo)

        if (
            "advertencias" in titulo_normalizado
            and "nota fiscal" in titulo_normalizado
        ):
            encontrada = hwnd
            return

        if (
            "inconsistencias encontradas em nota fiscal"
            in titulo_normalizado
        ):
            encontrada = hwnd

    win32gui.EnumWindows(enum_window, None)
    return encontrada


def _fechar_advertencias_nota_se_existir() -> bool:
    """
    Close the Nota Fiscal warnings/inconsistencies window when visible.

    First tries ESC. If it remains open, clicks the child control whose
    caption is 'Fechar'.
    """
    hwnd = _buscar_janela_advertencias_nota()

    if not hwnd:
        return False

    titulo = win32gui.GetWindowText(hwnd).strip()

    print(
        "[OS10] Tela de Advertências/Inconsistências encontrada | "
        f"TITULO={titulo}"
    )

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    _sleep(0.3)

    print(
        "[OS10] Tentando fechar Advertências/Inconsistências com ESC."
    )
    pyautogui.press("esc")
    _sleep(0.7)

    if not (
        win32gui.IsWindow(hwnd)
        and win32gui.IsWindowVisible(hwnd)
    ):
        print(
            "[OS10] Advertências/Inconsistências fechada com ESC."
        )
        return True

    botao_fechar: int | None = None

    def enum_child(child_hwnd: int, _: object) -> None:
        nonlocal botao_fechar

        if botao_fechar is not None:
            return

        texto = win32gui.GetWindowText(child_hwnd).strip()

        if normalizar_titulo(texto) == "fechar":
            botao_fechar = child_hwnd

    win32gui.EnumChildWindows(
        hwnd,
        enum_child,
        None,
    )

    if botao_fechar:
        left, top, right, bottom = win32gui.GetWindowRect(
            botao_fechar
        )

        x = left + ((right - left) // 2)
        y = top + ((bottom - top) // 2)

        print(
            "[OS10] Clicando no botão Fechar da tela "
            "Advertências/Inconsistências."
        )

        pyautogui.click(x, y)
        _sleep(0.8)

    fechou = not (
        win32gui.IsWindow(hwnd)
        and win32gui.IsWindowVisible(hwnd)
    )

    if fechou:
        print(
            "[OS10] Advertências/Inconsistências fechada."
        )
    else:
        print(
            "[OS10] Não foi possível fechar "
            "Advertências/Inconsistências."
        )

    return fechou


def _validar_nota_fiscal_apos_salvar(
    max_tentativas: int = 2,
) -> int:
    """
    Confirm that TFNfCab is really active before continuing after CTRL+S.

    The check is attempted at most twice. Atenção/Erro/Aviso popups are
    confirmed with ENTER. The warnings/inconsistencies window is treated as
    a failure because navigation must not continue while it is open.

    Raises RuntimeError after the final failed attempt. The caller's existing
    exception handler then takes the screenshot, sends the error notification,
    closes the transaction screens and continues with the next note.
    """
    ultimo_detalhe = ""

    for tentativa in range(1, max_tentativas + 1):
        print(
            "[OS10] Validando retorno após CTRL + S | "
            f"tentativa={tentativa}/{max_tentativas}"
        )

        # Pode haver Atenção / Erro / Aviso em sequência.
        for _ in range(3):
            if not confirmar_atencao_se_existir(timeout=1):
                break

            print(
                "[OS10] Popup após CTRL + S confirmado com ENTER."
            )
            _sleep(0.4)

        tela_advertencias = _buscar_janela_advertencias_nota()

        if tela_advertencias:
            titulo_advertencias = win32gui.GetWindowText(
                tela_advertencias
            ).strip()

            ultimo_detalhe = (
                "Tela de Advertências/Inconsistências ainda aberta: "
                f"{titulo_advertencias}"
            )

            print(
                "[OS10] Nota Fiscal ainda não está pronta para navegar | "
                f"{ultimo_detalhe}"
            )

            _sleep(1)
            continue

        tela_nota = _aguardar_janela_classe(
            "TFNfCab",
            timeout=3,
        )

        if not tela_nota:
            ultimo_detalhe = (
                "TFNfCab não foi encontrada."
            )

            print(
                "[OS10] Nota Fiscal não encontrada | "
                f"tentativa={tentativa}/{max_tentativas}"
            )

            _sleep(1)
            continue

        try:
            win32gui.SetForegroundWindow(
                tela_nota
            )
        except Exception:
            pass

        _sleep(0.7)

        janela_ativa = win32gui.GetForegroundWindow()
        classe_ativa = win32gui.GetClassName(
            janela_ativa
        )
        titulo_ativo = win32gui.GetWindowText(
            janela_ativa
        ).strip()

        print(
            "[OS10] Conferência da janela após CTRL + S | "
            f"CLASS={classe_ativa} | "
            f"TITULO={titulo_ativo}"
        )

        if classe_ativa == "TFNfCab":
            # Confere mais uma vez que nenhum modal apareceu após o foco.
            if not _buscar_janela_advertencias_nota():
                print(
                    "[OS10] Nota Fiscal confirmada e pronta "
                    "para continuar o fluxo."
                )
                return tela_nota

        ultimo_detalhe = (
            f"Janela ativa: CLASS={classe_ativa} | "
            f"TITULO={titulo_ativo}"
        )

        print(
            "[OS10] Nota Fiscal ainda não está pronta | "
            f"tentativa={tentativa}/{max_tentativas}"
        )

        _sleep(1)

    raise RuntimeError(
        "Após o CTRL + S, a Nota Fiscal não ficou pronta "
        f"depois de {max_tentativas} tentativas. "
        f"{ultimo_detalhe}"
    )


def fechar_telas_lancamento() -> None:
    """Close only OS10 transaction windows, keeping the Agro main screen open."""
    classes_para_fechar = (
        "TFPlacaVeiculos",
        "TFrGerarNFFrota",
        "TFPagCompraDupPag",
        "TFAcertoFinanceiro",
        "TFNfCab",
    )

    print("[OS10] Fechando telas do lançamento atual.")

    for _ in range(10):
        fechou_alguma = False

        # Fecha primeiro a tela de Advertências/Inconsistências, pois ela pode
        # bloquear o fechamento da Nota Fiscal que está por baixo.
        if _fechar_advertencias_nota_se_existir():
            _sleep(0.5)
            fechou_alguma = True
            continue

        # Se algum aviso simples aparecer durante o fechamento, confirma antes.
        if confirmar_atencao_se_existir(timeout=1):
            _sleep(0.5)
            fechou_alguma = True

        for class_name in classes_para_fechar:
            hwnd = _janela_visivel_por_classe(class_name)

            if not hwnd:
                continue

            titulo = win32gui.GetWindowText(hwnd).strip() or class_name
            print(f"[OS10] Fechando tela: {titulo} | CLASS={class_name}")

            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass

            _sleep(0.3)
            pyautogui.hotkey("ctrl", "f4")
            _sleep(0.8)
            fechou_alguma = True
            break

        if not fechou_alguma:
            break

    telas_restantes = []

    for class_name in classes_para_fechar:
        hwnd = _janela_visivel_por_classe(class_name)
        if hwnd:
            telas_restantes.append(
                win32gui.GetWindowText(hwnd).strip() or class_name
            )

    if telas_restantes:
        raise RuntimeError(
            "Não foi possível fechar todas as telas do lançamento: "
            + ", ".join(telas_restantes)
        )

    print("[OS10] Telas do lançamento fechadas. Pronto para a próxima linha.")


def _finalizar_acerto_financeiro_pos_pagamento(
    dados: dict[str, str],
) -> None:
    """
    Finaliza o pagamento, salva o Acerto Financeiro e retorna para a Nota Fiscal.

    Fluxo correto:
    1. O primeiro CTRL+S já foi dado em Pagamento com Duplicatas.
    2. Aguarda e foca TFAcertoFinanceiro.
    3. Dá o segundo CTRL+S.
    4. Aguarda TFNfCab voltar.
    5. Foca TFNfCab.
    6. Só então executa ALT+I e continua o lançamento.
    """
    local_nf = str(dados.get("LOCALNF", "") or "").strip()
    numero_pedido = str(dados.get("NUM_PED", "") or "").strip()

    if not local_nf:
        raise RuntimeError("LOCALNF não informado pela consulta.")

    if not numero_pedido:
        raise RuntimeError("NUM_PED não informado pela consulta.")

    # ========================================================
    # 1 - PRIMEIRO CTRL+S JÁ FOI DADO EM PAGAMENTO DUPLICATAS
    #     AGUARDA ACERTO FINANCEIRO
    # ========================================================

    print(
        "[OS10] Aguardando Acerto Financeiro "
        "após o primeiro CTRL + S."
    )

    tela_acerto = _aguardar_janela_classe(
        "TFAcertoFinanceiro",
        timeout=15,
    )

    if not tela_acerto:
        raise RuntimeError(
            "Tela Acerto Financeiro não apareceu "
            "após o primeiro CTRL + S."
        )

    titulo_acerto = win32gui.GetWindowText(tela_acerto).strip()

    print(
        "[OS10] Acerto Financeiro encontrado | "
        f"HWND={tela_acerto} | "
        f"TITULO={titulo_acerto}"
    )

    try:
        if win32gui.IsIconic(tela_acerto):
            win32gui.ShowWindow(
                tela_acerto,
                win32con.SW_RESTORE,
            )
            _sleep(0.3)

        win32gui.SetForegroundWindow(
            tela_acerto
        )

    except Exception:
        focar_janela_por_titulo(
            "Acerto Financeiro",
            timeout=5,
        )

    _sleep(0.7)

    # ========================================================
    # 2 - SEGUNDO CTRL + S NO ACERTO FINANCEIRO
    # ========================================================

    print(
        "[OS10] Acerto Financeiro focado. "
        "Enviando segundo CTRL + S."
    )

    pyautogui.hotkey(
        "ctrl",
        "s",
    )

    _sleep(1)

    tratar_validacao_acerto_financeiro(dados)

    if confirmar_atencao_se_existir(
        timeout=2
    ):
        print(
            "[OS10] Atenção após segundo CTRL + S confirmada."
        )
        _sleep(0.5)

    # ========================================================
    # 3 - DEPOIS DO SEGUNDO CTRL+S DEVE VOLTAR PARA TFNfCab
    # ========================================================

    print(
        "[OS10] Aguardando retorno para Nota Fiscal | "
        "CLASS=TFNfCab"
    )

    tela_nota = _aguardar_janela_classe(
        "TFNfCab",
        timeout=15,
    )

    if not tela_nota:
        print(
            "[OS10] Nenhuma tela esperada apareceu após Acerto Financeiro. Reiniciando Agro."
        )

        reiniciar_agro()

        raise RuntimeError(
            "Nenhum retorno esperado após Acerto Financeiro. Agro reiniciado."
        )

    titulo_nota = win32gui.GetWindowText(
        tela_nota
    ).strip()

    print(
        "[OS10] Nota Fiscal encontrada após segundo CTRL + S | "
        f"HWND={tela_nota} | "
        f"TITULO={titulo_nota}"
    )

    # ========================================================
    # 4 - FOCA TFNfCab ANTES DO ALT+I
    # ========================================================

    print(
        "[OS10] Focando Nota Fiscal antes do ALT + I."
    )

    try:
        if win32gui.IsIconic(tela_nota):
            win32gui.ShowWindow(
                tela_nota,
                win32con.SW_RESTORE,
            )
            _sleep(0.3)

        win32gui.SetForegroundWindow(
            tela_nota
        )

    except Exception:
        if not focar_janela_por_titulo(
            "Nota Fiscal",
            timeout=5,
        ):
            raise RuntimeError(
                "Não foi possível focar a tela Nota Fiscal "
                "antes do ALT + I."
            )

    _sleep(0.8)

    # Confirma que a janela ativa é realmente TFNfCab.
    janela_ativa = win32gui.GetForegroundWindow()
    classe_ativa = win32gui.GetClassName(janela_ativa)
    titulo_ativo = win32gui.GetWindowText(janela_ativa).strip()

    print(
        "[OS10] Janela ativa antes do ALT + I | "
        f"CLASS={classe_ativa} | "
        f"TITULO={titulo_ativo}"
    )

    if classe_ativa != "TFNfCab":
        # Faz uma última tentativa de foco antes de bloquear o fluxo.
        try:
            win32gui.SetForegroundWindow(
                tela_nota
            )
            _sleep(0.5)
        except Exception:
            pass

        janela_ativa = win32gui.GetForegroundWindow()
        classe_ativa = win32gui.GetClassName(janela_ativa)

        if classe_ativa != "TFNfCab":
            raise RuntimeError(
                "A tela Nota Fiscal foi encontrada, mas não ficou ativa. "
                f"CLASS ativa={classe_ativa}. "
                "ALT + I não foi enviado para evitar entrada em tela errada."
            )

    # ========================================================
    # 5 - AGORA SIM ALT + I
    # ========================================================

    print(
        "[OS10] Nota Fiscal focada. Comando: ALT + I"
    )

    pyautogui.hotkey(
        "alt",
        "i",
    )

    # Aguarda a aba/tela terminar de responder ao ALT + I.
    _sleep(1.5)

    print(
        "[OS10] Comando: SHIFT + TAB"
    )

    pyautogui.hotkey(
        "shift",
        "tab",
    )

    # Dá tempo para o foco estabilizar antes de navegar para a direita.
    _sleep(1.0)

    print(
        "[OS10] Comando: RIGHT 3x"
    )

    for indice in range(1, 4):
        print(
            f"[OS10] Comando: RIGHT {indice}/3"
        )

        pyautogui.press(
            "right"
        )

        _sleep(0.5)

    _sleep(0.5)

    print(
        "[OS10] Comando: TAB"
    )

    pyautogui.press(
        "tab"
    )

    _sleep(0.3)

    # ========================================================
    # 6 - LOCALNF
    # ========================================================

    print(
        f"[OS10] Informando LOCALNF: {local_nf}"
    )

    _write_value(
        "LOCALNF",
        local_nf,
    )

    print(
        "[OS10] Comando: TAB"
    )

    pyautogui.press(
        "tab"
    )

    _sleep(0.5)

    # ========================================================
    # 7 - SOMENTE CONFIGURAÇÃO 504 ENTRA NO FLUXO FROTA
    # ========================================================
    # Todas as configurações seguem o mesmo fluxo até aqui.
    # A única diferença é depois do LOCALNF.

    if _configuracao_e_504(
        dados
    ):
        print(
            "[OS10] Configuração 504 detectada. "
            "Executando fluxo Frota."
        )

        _executar_fluxo_config_504(
            dados
        )
    else:
        print(
            "[OS10] Configuração diferente de 504. "
            "Sem tela Frota. Continuando fluxo."
        )

    # ========================================================
    # 8 - CONTINUA FLUXO IGUAL PARA TODAS AS CONFIGURAÇÕES
    # ========================================================

    print(
        "[OS10] Comando: ALT + E"
    )

    pyautogui.hotkey(
        "alt",
        "e",
    )

    _sleep(0.5)

    print(
        "[OS10] Comando: TAB 2x"
    )

    pyautogui.press(
        "tab",
        presses=2,
        interval=0.2,
    )

    _sleep(0.3)

    print(
        f"[OS10] Informando NUM_PED: {numero_pedido}"
    )

    _write_value(
        "NUM_PED",
        numero_pedido,
    )

    # ========================================================
    # 9 - SALVAMENTO FINAL
    # ========================================================

    print(
        "[OS10] Comando: CTRL + S final"
    )

    pyautogui.hotkey(
        "ctrl",
        "s",
    )

    print("[OS10] Aguardando 10 segundos para garantir salvamento da nota.")
    _sleep(10)

    tratar_tf_form_erros_final(dados)

    if confirmar_atencao_se_existir(
        timeout=2
    ):
        print(
            "[OS10] Atenção após CTRL + S final confirmada."
        )
        _sleep(1)

    # ========================================================
    # 10 - FECHA AS TELAS E CONTINUA A PRÓXIMA LINHA
    # ========================================================

    fechar_telas_lancamento()


def processar_pagamento_tela_aberta(
    pedido: dict,
    dados: dict[str, str],
) -> None:
    """Fill and save payment when Pagamento com Duplicatas is already open."""
    tipo_pgto = str(pedido["tipopgto"]).strip().upper()

    if not tela_pagamento_duplicatas_aberta():
        raise RuntimeError("Tela 'Pagamento com Duplicatas' não abriu.")

    focar_janela_por_titulo("Pagamento com Duplicatas", timeout=30)
    clicar_regiao_pagamento()

    if tipo_pgto == "B":
        preencher_boleto(pedido)
    elif tipo_pgto == "D":
        preencher_deposito(pedido)
    elif tipo_pgto == "P":
        preencher_pix(pedido)
    elif tipo_pgto == "A":
        print(
            "[OS10] Tipo de pagamento A. "
            "Nenhuma ação financeira necessária."
        )
    else:
        raise ValueError(f"TIPOPGTO não mapeado: {tipo_pgto}")

    salvar_pagamento(dados)
    _finalizar_acerto_financeiro_pos_pagamento(dados)


def executar_acerto_financeiro(pedido: dict) -> None:
    """Standalone version of the supplied financial flow."""
    tipo_pgto = str(pedido["tipopgto"]).strip().upper()

    focar_janela_por_titulo("Nota Fiscal", timeout=30)

    pressionar_alt_a()
    time.sleep(2)

    validar_tela_valores_pendentes(pedido, timeout=3)

    if not tela_pagamento_duplicatas_aberta():
        raise RuntimeError("Tela 'Pagamento com Duplicatas' não abriu.")

    focar_janela_por_titulo("Pagamento com Duplicatas", timeout=30)
    clicar_regiao_pagamento()

    if tipo_pgto == "B":
        preencher_boleto(pedido)
    elif tipo_pgto == "D":
        preencher_deposito(pedido)
    elif tipo_pgto == "P":
        preencher_pix(pedido)
    elif tipo_pgto == "A":
        print(
            "[OS10] Tipo de pagamento A. "
            "Nenhuma ação financeira necessária."
        )
    else:
        raise ValueError(f"TIPOPGTO não mapeado: {tipo_pgto}")

    salvar_pagamento()



def tratar_confirma_imposto(hwnd: int) -> None:
    """
    Trata a tela:

    Título:
    Confirma Imposto

    Classe:
    TFRes

    Usa o HWND da janela já identificada.
    """

    titulo = win32gui.GetWindowText(hwnd)
    classe = win32gui.GetClassName(hwnd)

    print(
        "[OS10] Tratando Confirma Imposto | "
        f"HWND={hwnd} | "
        f"CLASS={classe} | "
        f"TITULO={titulo}"
    )

    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(
                hwnd,
                win32con.SW_RESTORE,
            )
            _sleep(0.5)

        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)

    except Exception as exc:
        raise RuntimeError(
            f"Não foi possível focar Confirma Imposto: {exc}"
        )

    _sleep(1)

    hwnd_ativo = win32gui.GetForegroundWindow()
    classe_ativa = win32gui.GetClassName(hwnd_ativo)

    print(
        "[OS10] Foco Confirma Imposto | "
        f"CLASS_ATIVA={classe_ativa}"
    )

    if classe_ativa != "TFRes":
        raise RuntimeError(
            "Confirma Imposto encontrada, mas não ficou ativa."
        )

    print("[OS10] Confirma Imposto: LEFT 2x")

    pyautogui.press(
        "left",
        presses=2,
        interval=0.3,
    )

    _sleep(0.5)

    print("[OS10] Confirma Imposto: ENTER")

    pyautogui.press("enter")

    _sleep(2)

    hwnd_verificacao = win32gui.FindWindow(
        "TFRes",
        None,
    )

    if (
        hwnd_verificacao
        and win32gui.IsWindowVisible(hwnd_verificacao)
        and "Confirma Imposto"
        in win32gui.GetWindowText(hwnd_verificacao)
    ):
        raise RuntimeError(
            "Confirma Imposto não fechou após confirmação."
        )

    print(
        "[OS10] Confirma Imposto fechada. "
        "Continuando fluxo."
    )



def validar_telas_inesperadas(
    nota: dict[str, Any],
) -> None:
    """
    Monitora telas abertas durante o fluxo.

    Regras:
    - Confirma Imposto: trata e continua.
    - Validação do Acerto Financeiro: trata conforme regra existente.
    - TFFormErros: interrompe e informa erro.
    - Qualquer tela inesperada: gera erro com classe e título.
    """

    telas: list[dict[str, str]] = []

    ignorar_classes = {
        "Au3Info",
        "Chrome_WidgetWin_1",
        "Progman",
        "TApplication",
        "WindowsForms10.Window.8.app.0.bb8560_r10_ad1",
    }

    def enum_window(hwnd: int, _: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return

        titulo = win32gui.GetWindowText(hwnd).strip()
        classe = win32gui.GetClassName(hwnd)

        if classe in ignorar_classes:
            return

        if titulo:
            telas.append(
                {
                    "hwnd": hwnd,
                    "titulo": titulo,
                    "classe": classe,
                }
            )

    win32gui.EnumWindows(
        enum_window,
        None,
    )

    for tela in telas:
        hwnd = tela["hwnd"]
        titulo = tela["titulo"]
        classe = tela["classe"]

        print(
            "[OS10] Tela detectada | "
            f"CLASS={classe} | "
            f"TITULO={titulo}"
        )

        if (
            classe == "TFRes"
            and "Confirma Imposto" in titulo
        ):
            print(
                "[OS10] Confirma Imposto detectada."
            )

            tratar_confirma_imposto(
                hwnd
            )

            return

        if (
            classe == "TFFormErros"
        ):
            screenshot = tirar_print_erro(nota)

            raise RuntimeError(
                "Tela de erro encontrada | "
                f"CLASS={classe} | "
                f"TITULO={titulo} | "
                f"SCREENSHOT={screenshot}"
            )



def tratar_tf_form_erros_final(
    nota: dict[str, Any],
) -> None:
    """
    Trata:
    Title: [A]dvertências/(I)nconsistências encontradas em Nota Fiscal
    Class: TFFormErros

    Regra:
    - Após CTRL+S final:
      - tira print;
      - reinicia Agro;
      - próxima nota.
    """

    hwnd = win32gui.FindWindow(
        "TFFormErros",
        "[A]dvertências/(I)nconsistências encontradas em Nota Fiscal",
    )

    if not hwnd or not win32gui.IsWindowVisible(hwnd):
        return

    print(
        "[OS10] Tela TFFormErros encontrada após CTRL+S final."
    )

    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

    _sleep(0.5)

    screenshot_path = tirar_print_erro(nota)

    print(
        "[OS10] Screenshot TFFormErros salvo: "
        f"{screenshot_path}"
    )

    print(
        "[OS10] Reiniciando Agro após inconsistências da Nota Fiscal."
    )

    reiniciar_agro()

    raise RuntimeError(
        "Advertências/Inconsistências encontradas em Nota Fiscal. "
        "Agro reiniciado."
    )







def lancar_nota(
    dados: dict[str, str],
    nota: dict[str, Any],
) -> None:
    """Launch OS10 note after CTRL + INSERT."""
    print("[OS10] Caminho: lançar nota.")

    print("[OS10] Informando REGRA_NOTACONF.")
    _write_value("REGRA_NOTACONF", dados["REGRA_NOTACONF"])

    print("[OS10] Comando: ENTER")
    pyautogui.press("enter")
    _sleep(1)

    print("[OS10] Aguardando tela: Dados da NF-e Recebida")
    if not wait_window_startswith("Dados da NF-e Recebida", timeout_seconds=15):
        raise RuntimeError("Tela 'Dados da NF-e Recebida' não apareceu.")

    print("[OS10] Tela encontrada: Dados da NF-e Recebida")
    pyautogui.press("esc")
    _sleep(0.5)

    data_emissao = formatar_data_emissao(dados["DTEMISSAO"])

    print(f"[OS10] Informando DTEMISSAO: {data_emissao}")
    _write_value("DTEMISSAO", data_emissao)

    print("[OS10] Comando: ENTER 3x")
    pyautogui.press("enter", presses=3, interval=0.5)
    _sleep(0.5)

    print("[OS10] Enviando SERIE: U")
    pyautogui.write("U", interval=0.03)
    _sleep(0.5)

    print("[OS10] Comando: ENTER")
    pyautogui.press("enter")
    _sleep(0.5)

    print("[OS10] Comando: DELET")
    pyautogui.press("delete")
    _sleep(0.5)

    print(f"[OS10] Informando NUMERO DA NOTA FISCAL: {dados['NUMERO_NF']}")
    _write_value("NUMERO_NF", dados["NUMERO_NF"])

    print("[OS10] Comando: ENTER")
    pyautogui.press("enter")
    _sleep(0.5)

    print(f"[OS10] Informando Fornecedor: {dados['FORNECEDOR']}")
    _write_value("FORNECEDOR", dados["FORNECEDOR"])

    print("[OS10] Comando: ENTER")
    pyautogui.press("enter")
    _sleep(0.5)

    print("[OS03] Verificando tela: Seleção de Endereço")
    if wait_window_startswith("Seleção de Endereço", timeout_seconds=2):
        print("[OS03] Tela encontrada: Seleção de Endereço")

        print("[OS03] Comando: RIGHT 6x")
        pyautogui.press("right", presses=6, interval=0.2)
        _sleep(0.3)

        print("[OS03] Comando: UP")
        pyautogui.press("up")
        _sleep(0.3)

        _write_value("EMITENTE_CNPJ", dados["EMITENTE_CNPJ"])

        print("[OS03] Comando: ENTER")
        pyautogui.press("enter")
        _sleep(0.8)
    else:
        print("[OS03] Tela Seleção de Endereço não apareceu. Seguindo fluxo.")

    for _ in range(2):
        _click_button_by_class_instance(
            parent_title="Nota Fiscal",
            class_name="TcxButton",
            instance=1,
            label="Apartir De",
        )
        _sleep(0.8)

    if wait_window_startswith("PRESTACAO DE SERVICO", timeout_seconds=2):
        print("[OS10] Tela encontrada: PRESTACAO DE SERVICO")
        _write_value("NUM_PED", dados["NUM_PED"])
        _sleep(0.5)

    print("[OS10] Comando: ALT + B")
    pyautogui.hotkey("alt", "b")
    _sleep(1.5)

    # Somente a Atenção (#32770) interrompe a nota e força o restart.
    # Se não aparecer, não mexemos em nenhuma tela e seguimos direto para CTRL+S.
    tratar_atencao_pos_alt_b(nota)

    validar_telas_inesperadas(nota)

    print("[OS10] Comando: CTRL + S")
    pyautogui.hotkey("ctrl", "s")
    _sleep(1.5)

    # Só continua para SHIFT+TAB se a Nota Fiscal estiver realmente pronta.
    # Verifica no máximo 2 vezes. Se não estiver, gera erro; o tratamento
    # externo envia a notificação, fecha as telas e segue para a próxima nota.
    _validar_nota_fiscal_apos_salvar(
        max_tentativas=2,
    )

    validar_telas_inesperadas(nota)

    print("[OS10] Comando: SHIFT + TAB")
    pyautogui.hotkey("shift", "tab")
    _sleep(0.5)

    print("[OS10] Comando: TAB")
    pyautogui.press("tab")
    _sleep(0.5)

    print("[OS10] Comando: DOWN 3x")
    pyautogui.press("down", presses=3, interval=0.2)
    _sleep(0.5)

    print("[OS10] Comando: RIGHT 2x")
    pyautogui.press("right", presses=2, interval=0.2)
    _sleep(0.5)

    decisao_retencao = analisar_retencoes(dados)

    validar_irrf(dados, decisao_retencao["IRRF"])
    _sleep(0.5)

    _voltar_grid()
    _sleep(0.5)

    validar_pis(dados, decisao_retencao["PIS"])
    _sleep(0.5)

    _voltar_grid()
    _sleep(0.5)

    validar_cofins(dados, decisao_retencao["COFINS"])
    _sleep(0.5)

    _voltar_grid()
    _sleep(0.5)

    validar_csll(
        dados,
        decisao_retencao["CSLL"]
    )

    validar_telas_inesperadas(nota)

    print("[OS10] FINALIZOU CSLL")

    _sleep(0.5)

    print("[OS10] Voltando grid após CSLL.")

    _voltar_grid()

    print("[OS10] GRID OK APÓS CSLL")

    _sleep(0.5)

    print("[OS10] INICIANDO ISS")

    validar_iss(
        dados,
        decisao_retencao["ISS"]
    )

    print("[OS10] FINALIZOU ISS")
    _sleep(0.5)

    _voltar_grid()
    _sleep(0.5)

    validar_inss(dados, decisao_retencao["INSS"])
    _sleep(0.5)

    print("[OS10] Comando: HOME")
    pyautogui.press("home")
    _sleep(0.5)

    print("[OS10] Comando: UP 10x")
    pyautogui.press("up", presses=10, interval=0.2)
    _sleep(0.5)

    if _to_float(dados["VALOR_INSS"]) > 0:
        print("[OS10] VALOR_INSS maior que zero. Clicando no botão INSS.")
        clicar_botao_inss()

    else:
        print("[OS10] VALOR_INSS zerado. Seguindo fluxo sem clicar no botão lateral.")

    for _ in range(2):
        print("[OS10] Comando: ALT + T")
        pyautogui.hotkey("alt", "t")
        _sleep(0.5)

    print("[OS10] Comando: ALT + A")
    pyautogui.hotkey("alt", "a")
    _sleep(2)

    pedido_financeiro = _montar_pedido_financeiro(dados)
    validar_tela_valores_pendentes(
        pedido_financeiro,
        timeout=3,
    )
    _sleep(1)

    janela_hwnd = win32gui.FindWindow("TFPagCompraDupPag", "Pagamento com Duplicatas")

    if not janela_hwnd:
        print("[OS10] Tela Pagamento com Duplicatas não encontrada.")
        raise RuntimeError("Tela Pagamento com Duplicatas não encontrada.")

    campo_total_produtos = _find_child_by_class_instance(
        parent_hwnd=janela_hwnd,
        class_name="TVsNum",
        instance=2,
    )

    if not campo_total_produtos:
        raise RuntimeError("Campo Total Produtos não encontrado.")

    total_produtos = win32gui.GetWindowText(
        campo_total_produtos
    ).strip()

    (
        valor_esperado_duplicata,
        diferenca,
        origem_valor_esperado,
    ) = _validar_valor_duplicata(
        total_produtos=total_produtos,
        dados=dados,
    )

    if diferenca == 0:
        print(
            "[OS10] Valor da duplicata confere. "
            f"Origem={origem_valor_esperado} | "
            f"Esperado={valor_esperado_duplicata:.2f}. "
            "Seguindo fluxo."
        )

    else:
        if diferenca >= 1:
            raise RuntimeError(
                "Valor da duplicata não confere. "
                f"Tela={total_produtos} | "
                f"Origem={origem_valor_esperado} | "
                f"Esperado={valor_esperado_duplicata:.2f} | "
                f"Diferença={diferenca:.2f}"
            )

        print(
            "[OS10] Diferença apenas de centavos. "
            f"Origem={origem_valor_esperado} | "
            f"Esperado={valor_esperado_duplicata:.2f} | "
            f"Diferença={diferenca:.2f}. "
            "Executando fluxo de ajuste."
        )

        # ==============================
        # FECHANDO ACERTO
        # ==============================

        _sleep(0.2)

        for _ in range(3):
            tela_pagamento = win32gui.FindWindow(
                "TFPagCompraDupPag",
                "Pagamento com Duplicatas",
            )

            if not tela_pagamento:
                break

            win32gui.SetForegroundWindow(tela_pagamento)
            _sleep(0.5)

            print("[OS10] Comando: CTRL + F4")
            pyautogui.hotkey("ctrl", "f4")
            _sleep(0.5)

        # Se a validação aparecer ao cancelar o acerto, reinicia o Agro e
        # encerra somente a nota atual. O loop externo continua na próxima.
        tratar_validacao_acerto_financeiro(dados)

        # Continua fluxo
        print("[OS10] Comando: CTRL + DEL")
        pyautogui.hotkey("ctrl", "delete")
        _sleep(0.5)

        print("[OS10] Comando: CTRL + F4")
        pyautogui.hotkey("ctrl", "f4")
        _sleep(0.2)

        # ==============================
        # CHEGANDO NA TELA DE IMPOSTO
        # ==============================

        tela_nota = win32gui.FindWindow("TFNfCab", "Nota Fiscal")

        if not tela_nota:
            raise RuntimeError("Tela Nota Fiscal não encontrada.")

        win32gui.SetForegroundWindow(tela_nota)
        _sleep(0.3)

        print("[OS10] Comando: ALT + G")
        pyautogui.hotkey("alt", "g")
        _sleep(0.5)

        for _ in range(8):
            print("[OS10] Comando: SHIFT + TAB 8x")
            pyautogui.hotkey("shift", "tab")
            _sleep(0.2)

        print("[OS10] Comando: DOWN 4x")
        pyautogui.press("down", presses=4, interval=0.2)
        _sleep(0.2)

        ajustar_centavos_pis_cofins_csll(diferenca)

        for _ in range(2):
            print("[OS10] Comando: ALT + T")
            pyautogui.hotkey("alt", "t")
            _sleep(0.5)

        print("[OS10] Comando: ALT + A")
        pyautogui.hotkey("alt", "a")
        _sleep(1)

        validar_tela_valores_pendentes(
            pedido_financeiro,
            timeout=3,
        )
        _sleep(0.5)

        # ==============================
        # VALIDANDO NOVAMENTE O ACERTO
        # ==============================

        janela_hwnd = win32gui.FindWindow(
            "TFPagCompraDupPag",
            "Pagamento com Duplicatas",
        )

        if not janela_hwnd:
            raise RuntimeError(
                "Tela Pagamento com Duplicatas não encontrada após ajuste de centavos."
            )

        campo_total_produtos = _find_child_by_class_instance(
            parent_hwnd=janela_hwnd,
            class_name="TVsNum",
            instance=2,
        )

        if not campo_total_produtos:
            raise RuntimeError(
                "Campo Total Produtos não encontrado após ajuste de centavos."
            )

        total_produtos_ajustado = win32gui.GetWindowText(
            campo_total_produtos
        ).strip()

        (
            valor_esperado_ajustado,
            diferenca_ajustada,
            origem_valor_ajustado,
        ) = _validar_valor_duplicata(
            total_produtos=total_produtos_ajustado,
            dados=dados,
        )

        print(
            "[OS10] Conferência após ajuste de centavos | "
            f"Tela={total_produtos_ajustado} | "
            f"Origem={origem_valor_ajustado} | "
            f"Esperado={valor_esperado_ajustado:.2f} | "
            f"Diferença={diferenca_ajustada:.2f}"
        )

        if diferenca_ajustada != 0:
            raise RuntimeError(
                "Valor da duplicata ainda não confere "
                "após ajuste de centavos. "
                f"Tela={total_produtos_ajustado} | "
                f"Origem={origem_valor_ajustado} | "
                f"Esperado={valor_esperado_ajustado:.2f} | "
                f"Diferença={diferenca_ajustada:.2f}"
            )

        print(
            "[OS10] Valor da duplicata validado após "
            "ajuste de centavos. Seguindo fluxo."
        )

   

    # ==============================
    # FLUXO DE PAGAMENTO INTEGRADO
    # ==============================

    pedido_financeiro = _montar_pedido_financeiro(dados)

    processar_pagamento_tela_aberta(
        pedido=pedido_financeiro,
        dados=dados,
    )


def _confirmar_atencao_recomendacao(timeout: int) -> bool:
    """Confirm payment recommendation warning when it appears."""
    timeout_final = time.time() + timeout

    while time.time() < timeout_final:
        tela_atencao = win32gui.FindWindow(
            "#32770",
            "Atenção",
        )

        if tela_atencao and win32gui.IsWindowVisible(tela_atencao):
            texto_hwnd = _find_child_by_class_instance(
                parent_hwnd=tela_atencao,
                class_name="Static",
                instance=2,
            )

            texto = ""

            if texto_hwnd:
                texto = win32gui.GetWindowText(texto_hwnd).strip()

            if "É Recomendável que as informações" in texto:
                botao_hwnd = _find_child_by_class_instance(
                    parent_hwnd=tela_atencao,
                    class_name="Button",
                    instance=1,
                )

                if not botao_hwnd:
                    raise RuntimeError(
                        "Botão da tela Atenção não encontrado."
                    )

                print("[OS10] Confirmando tela Atenção.")
                win32gui.PostMessage(
                    botao_hwnd,
                    win32con.BM_CLICK,
                    0,
                    0,
                )
                _sleep(0.1)

                return True

            return False

        _sleep(0.1)

    return False


def _aguardar_janela_classe(
    class_name: str,
    timeout: int,
) -> int | None:
    """Wait for a visible top-level window by class name."""
    timeout_final = time.time() + timeout

    while time.time() < timeout_final:
        hwnd = win32gui.FindWindow(
            class_name,
            None,
        )

        if hwnd and win32gui.IsWindowVisible(hwnd):
            return hwnd

        _sleep(0.2)

    return None
