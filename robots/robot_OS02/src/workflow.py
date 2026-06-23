"""Run the OS20 workflow steps.

Query Ticket Log API for lots above 95% received and import their notes
into Oracle incrementally — lotes already at 100% are skipped entirely,
and notes already imported (by CHAVE_ACESSO) are never re-inserted.

Developed by: MATHEUS CORREA
Updated by: MATHEUS CORREA
Last Modified: 2026-06-16
Version: 2.0.0
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pyautogui
import requests

from config import (
    AGRO_EXE,
    COMPUTADOR_ROBO,
    TICKETLOG_AUTHORIZATION,
    TICKETLOG_BASE_URL,
    TICKETLOG_CODIGO_CLIENTE,
)
from core.database import (
    buscar_executando,
    buscar_proximo_pendente,
    complete_task,
    fail_task,
    get_connection,
    marcar_executando,
)
from robots.robot_OS02.src.agro_alerts import (
    confirm_attention_popup,
    confirm_establishment_selection,
)
from robots.robot_OS02.src.agro_app import kill_agro_process, start_agro
from robots.robot_OS02.src.agro_estab import (
    focus_window,
    switch_establishment,
    wait_window_startswith,
)
from robots.robot_OS02.src.agro_login import login_agro
from robots.robot_OS02.src.database import (
    atualizar_notas_lancadas_diferente,
    buscar_chaves_lote,
    buscar_lotes_completos,
    buscar_notas_para_lancar,
    get_os20_connection,
    inserir_itens_nota,
    inserir_nota,
    marcar_nota_lancada,
    upsert_status_lote,
)
from robots.robot_OS02.src.lancamento import lancar_nota_162
from robots.robot_OS02.src.notifier import (
    enviar_relatorio_importacao,
    notify_conclusao,
    notify_error,
)

CODIGO_TIPO_CARTAO = 4

DATA_INICIAL = "2026-04-15"
DATA_FINAL = "2026-06-30"

PERCENTUAL_MINIMO = Decimal("95")

# Pause between each establishment's note queries to avoid API rate limiting.
# 0.5 s is conservative; lower only if the API proves more permissive.
_DELAY_ENTRE_ESTABELECIMENTOS = 0.5

# Maximum notes to launch per run — increase after testing.
LIMITE_NOTAS_TESTE = 2


def _fazer_get(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
    timeout: int = 60,
    ignorar_status: set[int] | None = None,
) -> Any:
    """Perform an authenticated GET request via the shared session.

    Returns None (instead of raising) for status codes in ignorar_status.
    """
    response = session.get(url, params=params, timeout=timeout)

    print(f"\nURL final: {response.url}")
    print(f"Status HTTP: {response.status_code}")

    if ignorar_status and response.status_code in ignorar_status:
        return None

    if response.status_code >= 400:
        raise RuntimeError(
            f"Erro na consulta Ticket Log. "
            f"Status HTTP: {response.status_code}. "
            f"Resposta: {response.text}"
        )

    return response.json()


def _gerar_janelas(
    data_inicial: str,
    data_final: str,
    max_dias: int = 32,
) -> list[tuple[str, str]]:
    """Split [data_inicial, data_final] into windows of at most max_dias days."""
    fmt = "%Y-%m-%d"
    inicio = datetime.strptime(data_inicial, fmt).date()
    fim = datetime.strptime(data_final, fmt).date()
    janelas: list[tuple[str, str]] = []
    atual = inicio
    while atual <= fim:
        fim_janela = min(atual + timedelta(days=max_dias - 1), fim)
        janelas.append((atual.strftime(fmt), fim_janela.strftime(fmt)))
        atual = fim_janela + timedelta(days=1)
    return janelas


def _consultar_lotes(session: requests.Session) -> list[dict[str, Any]]:
    url = f"{TICKETLOG_BASE_URL}/wsConsultaColetaNotasPostos/consultarLotes"
    lotes_por_codigo: dict[int, dict[str, Any]] = {}

    for data_ini, data_fim in _gerar_janelas(DATA_INICIAL, DATA_FINAL):
        params: dict[str, Any] = {
            "codigoCliente": TICKETLOG_CODIGO_CLIENTE,
            "codigoTipoCartao": CODIGO_TIPO_CARTAO,
            "dataInicial": data_ini,
            "dataFinal": data_fim,
        }
        for lote in _fazer_get(session, url, params=params).get("lotes", []):
            codigo = int(lote.get("codigoLote"))
            lotes_por_codigo[codigo] = lote

    return list(lotes_por_codigo.values())


def _consultar_estabelecimentos_lote(
    session: requests.Session,
    codigo_lote: int | str,
) -> list[dict[str, Any]]:
    url = (
        f"{TICKETLOG_BASE_URL}/wsConsultaColetaNotasPostos/"
        f"consultarEstabelecimentosLote/{codigo_lote}"
    )
    return _fazer_get(session, url).get("estabelecimentos", [])


def _consultar_notas_eletronicas(
    session: requests.Session,
    codigo_lote: int | str,
    codigo_estabelecimento: int | str,
) -> list[dict[str, Any]]:
    url = (
        f"{TICKETLOG_BASE_URL}/wsConsultaColetaNotasPostos/"
        "consultarNotasEletronicasEstabelecimento"
    )
    params = {
        "codigoLote": codigo_lote,
        "codigoEstabelecimento": codigo_estabelecimento,
    }
    data = _fazer_get(session, url, params=params, ignorar_status={460})
    return data.get("notas", []) if data is not None else []


def _consultar_notas_manuais(
    session: requests.Session,
    codigo_lote: int | str,
    codigo_estabelecimento: int | str,
) -> list[dict[str, Any]]:
    url = (
        f"{TICKETLOG_BASE_URL}/wsConsultaColetaNotasPostos/"
        "consultarNotasManuaisEstabelecimento"
    )
    params = {
        "codigoLote": codigo_lote,
        "codigoEstabelecimento": codigo_estabelecimento,
    }
    data = _fazer_get(session, url, params=params, ignorar_status={460})
    return data.get("notas", []) if data is not None else []


def _calcular_percentual_recebido(
    estabelecimentos: list[dict[str, Any]],
) -> tuple[Decimal, Decimal, Decimal]:
    """Return (percentual, valor_total, valor_recebido) for a lot."""
    valor_total_receber = Decimal("0")
    valor_total_recebido = Decimal("0")

    for est in estabelecimentos:
        valor = _converter_decimal(est.get("valorTotal"))
        valor_total_receber += valor

        if est.get("dataFechamentoRecolhimento"):
            valor_total_recebido += valor

    if valor_total_receber <= 0:
        return Decimal("0"), valor_total_receber, valor_total_recebido

    percentual = (valor_total_recebido / valor_total_receber) * Decimal("100")
    return percentual, valor_total_receber, valor_total_recebido


def _converter_decimal(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")
    texto = str(valor).strip()
    if not texto:
        return Decimal("0")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return Decimal(texto)


def _recuperar_agro() -> bool:
    """Close stray windows and return focus to AGRO-AG.

    Tries Escape + Ctrl+F4 first; falls back to a full Agro restart only
    if AGRO-AG is no longer reachable.  Returns True when AGRO-AG is ready.
    """
    for _ in range(3):
        pyautogui.press("escape")
        time.sleep(0.3)
    for _ in range(3):
        pyautogui.hotkey("ctrl", "f4")
        time.sleep(0.5)

    if wait_window_startswith("AGRO-AG", timeout_seconds=5):
        focus_window("AGRO-AG")
        return True

    print("[OS02] AGRO-AG não encontrado — reiniciando Agro...")
    kill_agro_process("Agro3C.exe")
    start_agro(AGRO_EXE)
    time.sleep(5)
    login_agro()
    confirm_attention_popup()
    confirm_establishment_selection()
    return wait_window_startswith("AGRO-AG", timeout_seconds=15)


def _imprimir_relatorio(relatorio: list[dict[str, Any]]) -> None:
    sucessos = [r for r in relatorio if r["status"] == "OK"]
    erros = [r for r in relatorio if r["status"] == "ERRO"]
    sep = "=" * 55
    print(f"\n{sep}")
    print("RELATÓRIO OS02 — LANÇAMENTO DE NOTAS")
    print(sep)
    print(f"Total: {len(relatorio)} | Sucesso: {len(sucessos)} | Erro: {len(erros)}")
    if sucessos:
        print("\nSUCESSO:")
        for r in sucessos:
            print(f"  Nota {r['nota']} | Estab {r['estab']} | Lote {r['lote']}")
    if erros:
        print("\nERROS:")
        for r in erros:
            print(f"  Nota {r['nota']} | Estab {r['estab']} | Lote {r['lote']} — {r.get('motivo', '')}")
    print(sep)


def _lancar_notas_em_agro(notas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Launch pending notes in Agro grouped by establishment.

    Processes at most LIMITE_NOTAS_TESTE notes per run.  On error per note,
    attempts soft recovery (Escape/Ctrl+F4) and falls back to a full Agro
    restart if AGRO-AG is unreachable.  Returns a report list with one entry
    per note (status "OK" or "ERRO").
    """
    # Build ordered flat list: [(estab, lote, chave, itens), ...] preserving
    # DB order (ESTAB ASC, LOTE ASC, NOTA ASC) and applying the test limit.
    vistas: set[str] = set()
    notas_unicas: list[str] = []
    itens_por_chave: dict[str, list[dict[str, Any]]] = {}
    for linha in notas:
        chave = (
            f"{linha['ESTAB']}|{linha['CODIGO_LOTE']}|"
            f"{linha['NUMERO_NOTA']}|{linha['SERIE']}"
        )
        itens_por_chave.setdefault(chave, []).append(linha)
        if chave not in vistas:
            vistas.add(chave)
            notas_unicas.append(chave)

    notas_unicas = notas_unicas[:LIMITE_NOTAS_TESTE]
    print(f"[OS02] Processando {len(notas_unicas)} nota(s) (limite: {LIMITE_NOTAS_TESTE})")

    kill_agro_process("Agro3C.exe")
    start_agro(AGRO_EXE)
    time.sleep(5)

    login_agro()
    print("[OS02] Login realizado.")

    confirm_attention_popup()
    confirm_establishment_selection()

    if not wait_window_startswith("AGRO-AG", timeout_seconds=15):
        raise RuntimeError("[OS02] Tela AGRO-AG não abriu após login.")

    relatorio: list[dict[str, Any]] = []
    estab_atual: int | None = None
    is_first_note = True

    with get_os20_connection() as conn:
        for idx, chave in enumerate(notas_unicas):
            itens = itens_por_chave[chave]
            header = itens[0]
            estab = int(header["ESTAB"])
            codigo_lote = int(header["CODIGO_LOTE"])
            numero_nota = str(header["NUMERO_NOTA"]).strip()
            serie = str(header["SERIE"]).strip()

            # Next note same estab? → keep form open; otherwise close it.
            is_last = idx == len(notas_unicas) - 1
            if not is_last:
                next_estab = int(itens_por_chave[notas_unicas[idx + 1]][0]["ESTAB"])
                close_form = next_estab != estab
            else:
                close_form = True

            print(f"\n[OS02] Nota {numero_nota} série {serie} | estab {estab} | lote {codigo_lote}")

            # Switch estab only when it changes
            if estab != estab_atual:
                if not switch_establishment(estab):
                    motivo = f"Falha ao trocar para estab {estab}"
                    print(f"[OS02] {motivo}. Pulando nota.")
                    relatorio.append({"nota": numero_nota, "estab": estab, "lote": codigo_lote, "status": "ERRO", "motivo": motivo})
                    continue
                estab_atual = estab
                is_first_note = True

            try:
                sucesso = lancar_nota_162(header, itens, is_first_note=is_first_note, close_form=close_form)

                if sucesso:
                    marcar_nota_lancada(conn, numero_nota, serie, codigo_lote)
                    relatorio.append({"nota": numero_nota, "estab": estab, "lote": codigo_lote, "status": "OK"})
                    print(f"[OS02] Nota {numero_nota} marcada como LANCADA.")

                    if not close_form:
                        # Same estab: press Ctrl+Insert to open next record
                        pyautogui.hotkey("ctrl", "insert")
                        time.sleep(6)
                        is_first_note = False
                    else:
                        is_first_note = True
                else:
                    motivo = "lancar_nota_162 retornou False"
                    print(f"[OS02] Falha ao lançar nota {numero_nota}. Tentando recuperar...")
                    relatorio.append({"nota": numero_nota, "estab": estab, "lote": codigo_lote, "status": "ERRO", "motivo": motivo})
                    notify_error(header, motivo)
                    if _recuperar_agro():
                        estab_atual = None
                        is_first_note = True
                    else:
                        print("[OS02] Recuperação falhou. Abortando lançamentos.")
                        break

            except Exception as exc:
                motivo = str(exc)
                print(f"[OS02] Erro inesperado na nota {numero_nota}: {motivo}")
                relatorio.append({"nota": numero_nota, "estab": estab, "lote": codigo_lote, "status": "ERRO", "motivo": motivo})
                notify_error(header, motivo)
                try:
                    kill_agro_process("Agro3C.exe")
                    start_agro(AGRO_EXE)
                    time.sleep(5)
                    login_agro()
                    confirm_attention_popup()
                    confirm_establishment_selection()
                    if not wait_window_startswith("AGRO-AG", timeout_seconds=15):
                        print("[OS02] Agro não recuperou. Abortando lançamentos.")
                        break
                except Exception as restart_exc:
                    print(f"[OS02] Falha ao reiniciar Agro: {restart_exc}. Abortando.")
                    break
                estab_atual = None
                is_first_note = True

    kill_agro_process("Agro3C.exe")
    print("[OS02] Agro encerrado.")
    return relatorio


def run_once(log_id: int | None = None) -> None:
    """OS02 main cycle.

    Phase 1 — Launch notes in Agro.
    Phase 2 — Consult TicketLog API when no notes are pending.

    U_ROBOT_LOG updated to CONCLUIDO on success, ERRO on unhandled exception.
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

            log_id = int(proximo["u_robot_log_id"])
            marcar_executando(connection, log_id, COMPUTADOR_ROBO)
            print(f"Tarefa log_id={log_id} marcada como EXECUTANDO.")

    try:
        _run_once_body(log_id)
    except Exception as exc:
        print(f"[OS02] Erro na execução: {exc}")
        try:
            with get_connection() as conn:
                fail_task(conn, log_id, f"Erro: {str(exc)[:3990]}")
            print(f"[OS02] U_ROBOT_LOG {log_id} → ERRO")
        except Exception as e2:
            print(f"[OS02] Falha ao marcar ERRO no log: {e2}")
        raise

    try:
        with get_connection() as conn:
            complete_task(conn, log_id, "Execução concluída.", computer_name=COMPUTADOR_ROBO)
        print(f"[OS02] U_ROBOT_LOG {log_id} → CONCLUIDO")
    except Exception as exc:
        print(f"[OS02] Falha ao marcar CONCLUIDO no log: {exc}")


def _run_once_body(log_id: int | None) -> None:
    print(f"[OS02] _run_once_body iniciado | log_id={log_id}")
    # ------------------------------------------------------------------
    # Pre-phase: mark notes already in NFCAB (not by this RPA) before anything
    # ------------------------------------------------------------------
    with get_os20_connection() as conn:
        atualizadas = atualizar_notas_lancadas_diferente(conn)
        if atualizadas:
            print(
                f"[OS02] {atualizadas} nota(s) marcada(s) como LANCADO DIFERENTE RPA.OS02."
            )

    # ------------------------------------------------------------------
    # Phase 1: launch pending notes in Agro (first batch first)
    # ------------------------------------------------------------------
    with get_os20_connection() as conn:
        notas_pendentes = buscar_notas_para_lancar(conn)

    if notas_pendentes:
        print(
            f"\n[OS02] {len(notas_pendentes)} linha(s) pendente(s) para lançar. Iniciando Agro..."
        )
        relatorio = _lancar_notas_em_agro(notas_pendentes)
        _imprimir_relatorio(relatorio)
        notify_conclusao(relatorio)
        print("[OS02] Fase 1 concluída. Próximo ciclo verificará notas restantes.")
        return

    # ------------------------------------------------------------------
    # Phase 2: no pending notes → consult TicketLog API
    # ------------------------------------------------------------------
    print("[OS02] Nenhuma nota pendente para lançar. Consultando API Ticket Log...")

    session = requests.Session()
    session.headers.update(
        {
            "Authorization": TICKETLOG_AUTHORIZATION,
            "Accept": "application/json",
        }
    )

    with get_os20_connection() as conn:

        lotes_completos = buscar_lotes_completos(conn)
        print(f"Lotes já 100% no banco: {len(lotes_completos)}")

        lotes = _consultar_lotes(session)

        if not lotes:
            raise RuntimeError("Nenhum lote encontrado para o período configurado.")

        total_lotes_processados = 0
        total_novas = 0
        total_ignoradas = 0
        lotes_resumo: list[dict[str, Any]] = []

        for lote in lotes:
            codigo_lote = int(lote.get("codigoLote"))

            if codigo_lote in lotes_completos:
                print(f"Lote {codigo_lote} — 100% completo, pulando.")
                continue

            estabelecimentos = _consultar_estabelecimentos_lote(session, codigo_lote)

            percentual, valor_total_lote, valor_recebido_lote = (
                _calcular_percentual_recebido(estabelecimentos)
            )

            if percentual < PERCENTUAL_MINIMO:
                print(
                    f"Lote {codigo_lote} — {percentual:.2f}% recebido "
                    f"(mínimo {PERCENTUAL_MINIMO}%). Ignorado."
                )
                upsert_status_lote(conn, codigo_lote, percentual, completo=False)
                conn.commit()
                continue

            lote_completo = percentual >= Decimal("100")
            total_lotes_processados += 1

            print(
                f"\nLote {codigo_lote} | {percentual:.2f}% | "
                f"{'COMPLETO' if lote_completo else 'PARCIAL'} | "
                f"R$ {valor_recebido_lote:.2f} / R$ {valor_total_lote:.2f}"
            )

            chaves_existentes = buscar_chaves_lote(conn, codigo_lote)
            notas_novas = 0
            notas_ignoradas = 0

            for idx, est in enumerate(estabelecimentos):
                codigo_est = est.get("codigoEstabelecimento")
                nome_est = est.get("estabelecimento") or ""

                notas_eletronicas = _consultar_notas_eletronicas(
                    session,
                    codigo_lote=codigo_lote,
                    codigo_estabelecimento=codigo_est,
                )
                notas_manuais = _consultar_notas_manuais(
                    session,
                    codigo_lote=codigo_lote,
                    codigo_estabelecimento=codigo_est,
                )

                for tipo_nota, notas in (
                    ("ELETRONICA", notas_eletronicas),
                    ("MANUAL", notas_manuais),
                ):
                    for nota in notas:
                        chave = nota.get("chaveAcesso")

                        if chave and chave in chaves_existentes:
                            notas_ignoradas += 1
                            continue

                        nota_id = inserir_nota(
                            conn,
                            codigo_lote=codigo_lote,
                            codigo_estabelecimento=codigo_est,
                            estabelecimento=nome_est,
                            tipo_nota=tipo_nota,
                            nota=nota,
                            valor_total_lote=valor_total_lote,
                            valor_recebido_lote=valor_recebido_lote,
                            percentual_recebido=percentual,
                        )
                        inserir_itens_nota(
                            conn,
                            nota_id,
                            nota.get("itens") or [],
                            codigo_lote=codigo_lote,
                            codigo_estabelecimento=int(codigo_est or 0),
                            chave_acesso=nota.get("chaveAcesso"),
                            numero_nota=str(nota.get("numero") or ""),
                        )

                        if chave:
                            chaves_existentes.add(chave)

                        notas_novas += 1

                conn.commit()

                # Rate limiting: avoid hammering the API between establishments.
                if idx < len(estabelecimentos) - 1:
                    time.sleep(_DELAY_ENTRE_ESTABELECIMENTOS)

            upsert_status_lote(conn, codigo_lote, percentual, completo=lote_completo)
            conn.commit()

            total_novas += notas_novas
            total_ignoradas += notas_ignoradas

            lotes_resumo.append(
                {
                    "codigo_lote": codigo_lote,
                    "percentual": percentual,
                    "novas": notas_novas,
                    "ignoradas": notas_ignoradas,
                    "valor_lote": valor_total_lote,
                }
            )

            print(
                f"  → Notas novas: {notas_novas} | " f"Já existentes: {notas_ignoradas}"
            )

    print("\nProcesso finalizado.")
    print(f"Lotes processados (>= {PERCENTUAL_MINIMO}%): {total_lotes_processados}")
    print(f"Notas importadas: {total_novas}")
    print(f"Notas já existentes (ignoradas): {total_ignoradas}")

    enviar_relatorio_importacao(
        total_novas=total_novas,
        total_ignoradas=total_ignoradas,
        lotes=lotes_resumo,
        data_inicial=DATA_INICIAL,
        data_final=DATA_FINAL,
    )


def run() -> None:
    """Run the legacy loop used by main.py."""
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"ERRO GERAL: {e}")

        print("Aguardando 20 segundos...\n")
        time.sleep(20)
