"""Shared OS07 nota processing queue — multi-machine, claim-based.

No DDL required — uses the existing USUARIO column as a claiming marker:
  USUARIO = 'OS07_FILA'  → note is in the shared pool, available to any machine
  USUARIO = '<computador>' → note is claimed and being processed by that machine

Flow per machine (all machines share the same queue):
  1. limpar_fila()      — reset EXECUTANDO rows stuck from a previous crash of THIS machine
  2. popular_fila()     — insert notes NOT already queued today (WHERE NOT EXISTS, safe for concurrent calls)
  3. claim_next_batch() — atomically claim 10 PENDENTE notes (FOR UPDATE SKIP LOCKED)
  4. marcar_concluido/erro() — mark the claimed note done or failed
  5. enviar_relatorio_final() — email summary for THIS machine's work today
"""

from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import oracledb

from config import EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST

_MINUTOS_POR_NOTA = 2.5

_EMAIL_TO = [
    "matheus.correa@ourosafra.com.br",
    "nfe.cereais@ourosafra.com.br",
    "alif.toledo@ourosafra.com.br",
    "isaque.ricardo@ourosafra.com.br",
    "hugo.arantes@ourosafra.com.br",
]


# ---------------------------------------------------------------------------
# Queue management
# ---------------------------------------------------------------------------


def limpar_fila(conn: oracledb.Connection, computador: str) -> None:
    """Remove linhas antigas e libera notas presas de crash desta máquina de volta ao pool.

    1. Apaga todos os registros de dias anteriores para esta máquina e do pool.
    2. Notas PENDENTE reivindicadas por esta máquina (crash anterior) são devolvidas
       ao pool compartilhado ('OS07_FILA') para serem reivindicadas novamente.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM U_OS07_FILA
             WHERE USUARIO     = :comp
               AND DT_INCLUSAO < TRUNC(SYSDATE)
            """,
            {"comp": computador},
        )
        if cur.rowcount:
            print(f"[fila] {cur.rowcount} registro(s) de dias anteriores removidos.")

        cur.execute(
            """
            DELETE FROM U_OS07_FILA
             WHERE USUARIO     = 'OS07_FILA'
               AND DT_INCLUSAO < TRUNC(SYSDATE)
            """,
        )
        if cur.rowcount:
            print(f"[fila] {cur.rowcount} registro(s) do pool de dias anteriores removidos.")

        cur.execute(
            """
            UPDATE U_OS07_FILA
               SET USUARIO = 'OS07_FILA'
             WHERE USUARIO     = :comp
               AND STATUS      = 'PENDENTE'
               AND DT_INCLUSAO >= TRUNC(SYSDATE)
            """,
            {"comp": computador},
        )
        if cur.rowcount:
            print(f"[fila] {cur.rowcount} nota(s) devolvidas ao pool após crash anterior.")

    conn.commit()


def limpar_fila_pos_execucao(conn: oracledb.Connection, computador: str) -> None:
    """Apaga todas as linhas desta máquina da fila após o ciclo completo.

    Chamada depois que o relatório final já foi enviado, então os dados
    já foram consumidos. Remove CONCLUIDO, ERRO e eventuais PENDENTE
    remanescentes do dia.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM U_OS07_FILA
             WHERE USUARIO     = :comp
               AND DT_INCLUSAO >= TRUNC(SYSDATE)
            """,
            {"comp": computador},
        )
        if cur.rowcount:
            print(f"[fila] {cur.rowcount} linha(s) removidas da fila após finalização.")
    conn.commit()


def popular_fila(
    conn: oracledb.Connection, notas: list[dict[str, Any]], computador: str
) -> None:
    """Insere notas no pool compartilhado da fila.

    USUARIO = 'OS07_FILA' — marca a nota como disponível para qualquer máquina.
    WHERE NOT EXISTS garante que notas já no pool hoje não sejam duplicadas,
    independente de qual máquina as inseriu.
    """
    agora = datetime.now()
    inseridos = 0

    with conn.cursor() as cur:
        for posicao, nota in enumerate(notas, start=1):
            previsao = agora + timedelta(minutes=posicao * _MINUTOS_POR_NOTA)
            cur.execute(
                """
                INSERT INTO U_OS07_FILA
                    (USUARIO, CONT_ID, NUMERONOTA, NOTACONF, ESTAB,
                     POSICAO, STATUS, DT_INCLUSAO, DT_PREVISAO)
                SELECT
                    'OS07_FILA', :cont_id, :numeronota, :notaconf, :estab,
                    :posicao, 'PENDENTE', SYSTIMESTAMP, :previsao
                FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1 FROM U_OS07_FILA
                     WHERE CONT_ID = :cont_id2
                       AND DT_INCLUSAO >= TRUNC(SYSDATE)
                )
                """,
                {
                    "cont_id": nota.get("U_FISCAL_IO_CONT_ID"),
                    "numeronota": str(nota.get("NUMERONOTA") or ""),
                    "notaconf": str(nota.get("NOTACONF") or ""),
                    "estab": str(nota.get("ESTAB") or ""),
                    "posicao": posicao,
                    "previsao": previsao,
                    "cont_id2": nota.get("U_FISCAL_IO_CONT_ID"),
                },
            )
            inseridos += cur.rowcount
        conn.commit()

    previsao_final = agora + timedelta(minutes=len(notas) * _MINUTOS_POR_NOTA)
    print(
        f"[fila] {inseridos} nota(s) adicionadas ao pool. "
        f"Previsão de término: {previsao_final.strftime('%H:%M')}."
    )


def claim_next_batch(
    conn: oracledb.Connection, computador: str, batch_size: int = 10
) -> int:
    """Reivindica atomicamente até batch_size notas do pool para esta máquina.

    Usa FOR UPDATE SKIP LOCKED para garantir que duas máquinas nunca
    reivindiquem a mesma nota simultaneamente — sem race conditions.

    Retorna o número de notas reivindicadas.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE U_OS07_FILA
               SET USUARIO = :comp
             WHERE ROWID IN (
                SELECT ROWID FROM U_OS07_FILA
                 WHERE USUARIO = 'OS07_FILA'
                   AND STATUS  = 'PENDENTE'
                   AND DT_INCLUSAO >= TRUNC(SYSDATE)
                 ORDER BY POSICAO ASC
                 FETCH FIRST :batch ROWS ONLY
                 FOR UPDATE SKIP LOCKED
             )
            """,
            {"comp": computador, "batch": batch_size},
        )
        claimed = cur.rowcount
        conn.commit()

    if claimed:
        print(f"[fila] {claimed} nota(s) reivindicada(s) para '{computador}'.")
    else:
        print(f"[fila] Nenhuma nota disponível no pool para '{computador}'.")
    return claimed


def marcar_concluido(
    conn: oracledb.Connection, cont_id: Any, computador: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE U_OS07_FILA
               SET STATUS           = 'CONCLUIDO',
                   DT_PROCESSAMENTO = SYSTIMESTAMP
             WHERE CONT_ID  = :cont_id
               AND USUARIO  = :comp
               AND DT_INCLUSAO >= TRUNC(SYSDATE)
            """,
            {"cont_id": cont_id, "comp": computador},
        )
        conn.commit()


def marcar_erro(
    conn: oracledb.Connection,
    cont_id: Any,
    computador: str,
    mensagem: str = "",
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE U_OS07_FILA
               SET STATUS           = 'ERRO',
                   DT_PROCESSAMENTO = SYSTIMESTAMP,
                   MENSAGEM         = :msg
             WHERE CONT_ID  = :cont_id
               AND USUARIO  = :comp
               AND DT_INCLUSAO >= TRUNC(SYSDATE)
            """,
            {"cont_id": cont_id, "comp": computador, "msg": mensagem[:4000]},
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Final report — scoped to this machine's work today
# ---------------------------------------------------------------------------


def _buscar_resumo(
    conn: oracledb.Connection, computador: str
) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) AS TOTAL,
                SUM(CASE WHEN STATUS = 'CONCLUIDO' THEN 1 ELSE 0 END) AS CONCLUIDOS,
                SUM(CASE WHEN STATUS = 'ERRO'      THEN 1 ELSE 0 END) AS ERROS,
                SUM(CASE WHEN STATUS = 'EXECUTANDO' THEN 1 ELSE 0 END) AS PENDENTES
            FROM U_OS07_FILA
            WHERE USUARIO = :comp
              AND DT_INCLUSAO >= TRUNC(SYSDATE)
            """,
            {"comp": computador},
        )
        row = cur.fetchone()
        cols = [c[0].lower() for c in cur.description]
        result = dict(zip(cols, row))
    return {k: int(v or 0) for k, v in result.items()}


def _buscar_erros_detalhe(
    conn: oracledb.Connection, computador: str
) -> list[dict[str, str]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT NUMERONOTA, NOTACONF, ESTAB, POSICAO, MENSAGEM
              FROM U_OS07_FILA
             WHERE USUARIO  = :comp
               AND STATUS   = 'ERRO'
               AND DT_INCLUSAO >= TRUNC(SYSDATE)
             ORDER BY POSICAO
            """,
            {"comp": computador},
        )
        return [
            {
                "numeronota": row[0] or "",
                "notaconf": row[1] or "",
                "estab": row[2] or "",
                "posicao": str(row[3] or ""),
                "mensagem": (row[4] or "")[:150],
            }
            for row in cur.fetchall()
        ]


_TH = "background:#fafafa;padding:9px 10px;text-align:left;border:1px solid #ddd;font-size:13px"


def _card(valor: int, label: str, bg: str, border: str) -> str:
    return (
        f'<div style="flex:1;min-width:120px;border-radius:8px;padding:14px 12px;'
        f'text-align:center;background:{bg};border-left:5px solid {border}">'
        f'<p style="font-size:30px;font-weight:bold;margin:0">{valor}</p>'
        f'<p style="font-size:12px;color:#555;margin:4px 0 0">{label}</p></div>'
    )


def _build_report_html(
    computador: str,
    total: int,
    concluidos: int,
    erros: int,
    pendentes: int,
    erros_detalhe: list[dict[str, str]],
) -> str:
    taxa = round(concluidos / total * 100, 1) if total else 0.0

    erros_rows = "".join(
        f"<tr><td>{e['posicao']}</td><td>{e['numeronota']}</td>"
        f"<td>{e['notaconf']}</td><td>{e['estab']}</td>"
        f"<td style='color:#c62828'>{e['mensagem']}</td></tr>"
        for e in erros_detalhe
    )
    erros_section = ""
    if erros_detalhe:
        erros_section = f"""
        <h2 style="font-size:17px;color:#333;border-bottom:2px solid #f7b500;padding-bottom:8px;margin-top:28px">
          Notas com Erro
        </h2>
        <table style="width:100%;border-collapse:collapse;margin-top:8px">
          <tr>
            <th style="{_TH}">Pos.</th>
            <th style="{_TH}">Nota</th>
            <th style="{_TH}">Conf</th>
            <th style="{_TH}">Estab</th>
            <th style="{_TH}">Motivo</th>
          </tr>
          {erros_rows}
        </table>"""

    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f4f5f6;font-family:Arial,sans-serif;font-size:15px;color:#333">
<div style="max-width:720px;margin:24px auto;background:#fff;border-radius:12px;
            border:1px solid #e5e5e5;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08)">
  <div style="background:#f7b500;padding:20px 26px;display:flex;
              justify-content:space-between;align-items:center">
    <img src="https://www.ourosafra.com.br/wp-content/uploads/2023/11/logo_ourosafra_sem-margens.png"
         alt="Ouro Safra" style="max-height:56px"/>
    <span style="color:#fff;font-size:15px;font-weight:bold;text-transform:uppercase;
                 letter-spacing:.4px">Excelência Operacional - VX360</span>
  </div>
  <div style="padding:30px 26px">
    <h1 style="font-size:22px;margin:0 0 6px">Relatório Final de Execução - OS07</h1>
    <p style="margin:0 0 20px;color:#666">
      Máquina: <strong>{computador}</strong>
      &nbsp;|&nbsp;
      Data: <strong>{datetime.now().strftime('%d/%m/%Y %H:%M')}</strong>
    </p>
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px">
      {_card(total,      "Total",      "#e3f2fd", "#1976d2")}
      {_card(concluidos, "Concluídos", "#e8f5e9", "#388e3c")}
      {_card(erros,      "Erros",      "#fff3e0", "#e65100")}
      {_card(pendentes,  "Em exec.",   "#f3e5f5", "#7b1fa2")}
    </div>
    <div style="background:#fff8e1;border-left:5px solid #f7b500;
                padding:14px 16px;border-radius:8px;margin-bottom:20px">
      Taxa de sucesso: <strong>{taxa}%</strong>
    </div>
    {erros_section}
  </div>
  <div style="background:#333;color:#fff;text-align:center;padding:14px;font-size:12px">
    Este é um e-mail enviado automaticamente. Por favor, não responda.
  </div>
</div>
</body></html>"""


def enviar_relatorio_final(conn: oracledb.Connection, computador: str) -> None:
    """Query queue stats for this machine today and send a summary email."""
    try:
        resumo = _buscar_resumo(conn, computador)
        erros_detalhe = _buscar_erros_detalhe(conn, computador)
    except Exception as exc:
        print(f"[queue_tracker] Erro ao buscar dados para relatório: {exc}")
        resumo = {"total": 0, "concluidos": 0, "erros": 0, "pendentes": 0}
        erros_detalhe = []

    total = resumo["total"]
    concluidos = resumo["concluidos"]
    erros = resumo["erros"]
    pendentes = resumo["pendentes"]

    print(
        f"\nRelatório OS07 | Máquina: {computador} | "
        f"Total: {total} | Concluídos: {concluidos} | Erros: {erros} | Em exec.: {pendentes}"
    )

    html = _build_report_html(computador, total, concluidos, erros, pendentes, erros_detalhe)

    msg = MIMEMultipart()
    msg["Subject"] = (
        f"VX360 OS07 - Relatório Final | {computador} | "
        f"Tentativas: {total} | Sucesso: {concluidos} | Erro: {erros}"
    )
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(_EMAIL_TO)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, 25, timeout=15) as server:
            server.ehlo()
            try:
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
            except smtplib.SMTPNotSupportedError:
                pass
            server.sendmail(EMAIL_FROM, _EMAIL_TO, msg.as_string())
        print("Relatório final enviado por e-mail.")
    except Exception as exc:
        print(f"Erro ao enviar relatório final: {exc}")
