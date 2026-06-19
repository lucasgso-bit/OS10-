"""Send import summary email for the OS20 Ticket Log note import cycle."""

from __future__ import annotations

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST, TICKETLOG_EMAIL_TO

_TH = (
    "background:#fafafa;padding:9px 10px;text-align:left;"
    "border:1px solid #ddd;font-size:13px"
)
_TD = "padding:8px 10px;border:1px solid #ddd;font-size:13px"


def _card(valor: int | str, label: str, bg: str, border: str) -> str:
    return (
        f'<div style="flex:1;min-width:120px;border-radius:8px;padding:14px 12px;'
        f'text-align:center;background:{bg};border-left:5px solid {border}">'
        f'<p style="font-size:28px;font-weight:bold;margin:0">{valor}</p>'
        f'<p style="font-size:12px;color:#555;margin:4px 0 0">{label}</p></div>'
    )


def _build_html(
    total_novas: int,
    total_ignoradas: int,
    lotes: list[dict],
    data_inicial: str,
    data_final: str,
) -> str:
    valor_total_importado = sum(l["valor_lote"] for l in lotes)

    lote_rows = "".join(
        f"<tr>"
        f"<td style='{_TD}'>{l['codigo_lote']}</td>"
        f"<td style='{_TD}'>{l['percentual']:.2f}%</td>"
        f"<td style='{_TD}'>{l['novas']}</td>"
        f"<td style='{_TD}'>{l['ignoradas']}</td>"
        f"<td style='{_TD}'>R$ {l['valor_lote']:,.2f}</td>"
        f"</tr>"
        for l in lotes
    )

    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f4f5f6;font-family:Arial,sans-serif;font-size:15px;color:#333">
<div style="max-width:760px;margin:24px auto;background:#fff;border-radius:12px;
            border:1px solid #e5e5e5;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08)">
  <div style="background:#f7b500;padding:20px 26px;display:flex;
              justify-content:space-between;align-items:center">
    <img src="https://www.ourosafra.com.br/wp-content/uploads/2023/11/logo_ourosafra_sem-margens.png"
         alt="Ouro Safra" style="max-height:56px"/>
    <span style="color:#fff;font-size:15px;font-weight:bold;text-transform:uppercase;
                 letter-spacing:.4px">Excelência Operacional - VX360</span>
  </div>
  <div style="padding:30px 26px">
    <h1 style="font-size:22px;margin:0 0 6px">Importação TicketLog — OS20</h1>
    <p style="margin:0 0 20px;color:#666">
      Período: <strong>{data_inicial} a {data_final}</strong>
      &nbsp;|&nbsp;
      Executado em: <strong>{datetime.now().strftime('%d/%m/%Y %H:%M')}</strong>
    </p>
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px">
      {_card(len(lotes), "Lotes Processados", "#e3f2fd", "#1976d2")}
      {_card(total_novas, "Notas Novas", "#e8f5e9", "#388e3c")}
      {_card(total_ignoradas, "Já Existentes", "#fff3e0", "#e65100")}
    </div>
    <div style="background:#fff8e1;border-left:5px solid #f7b500;
                padding:14px 16px;border-radius:8px;margin-bottom:24px">
      Valor total importado: <strong>R$ {valor_total_importado:,.2f}</strong>
    </div>
    <h2 style="font-size:17px;color:#333;border-bottom:2px solid #f7b500;
               padding-bottom:8px;margin-top:0">
      Detalhamento por Lote
    </h2>
    <table style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr>
        <th style="{_TH}">Lote</th>
        <th style="{_TH}">% Recebido</th>
        <th style="{_TH}">Notas Novas</th>
        <th style="{_TH}">Já Existentes</th>
        <th style="{_TH}">Valor do Lote</th>
      </tr>
      {lote_rows}
    </table>
    <p style="margin-top:20px;font-size:12px;color:#888">
      As notas com STATUS = PENDENTE na tabela U_TICKETLOG_NOTAS_LOTE estão aguardando lançamento.
    </p>
  </div>
  <div style="background:#333;color:#fff;text-align:center;padding:14px;font-size:12px">
    Este é um e-mail enviado automaticamente. Por favor, não responda.
  </div>
</div>
</body></html>"""


def enviar_relatorio_importacao(
    total_novas: int,
    total_ignoradas: int,
    lotes: list[dict],
    data_inicial: str,
    data_final: str,
) -> None:
    """Send import summary email.

    lotes: list of dicts — keys: codigo_lote, percentual, novas, ignoradas, valor_lote
    """
    if not TICKETLOG_EMAIL_TO:
        print("TICKETLOG_EMAIL_TO não configurado — e-mail não enviado.")
        return

    if total_novas == 0 and not lotes:
        print("Nenhuma nota nova — e-mail não enviado.")
        return

    email_to = [e.strip() for e in TICKETLOG_EMAIL_TO.split(",") if e.strip()]

    msg = MIMEMultipart()
    msg["Subject"] = (
        f"VX360 OS20 — Importação TicketLog | "
        f"Novas: {total_novas} | "
        f"Período: {data_inicial} a {data_final}"
    )
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(email_to)
    msg.attach(MIMEText(_build_html(total_novas, total_ignoradas, lotes, data_inicial, data_final), "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, 25, timeout=15) as server:
            server.ehlo()
            try:
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
            except smtplib.SMTPNotSupportedError:
                pass
            server.sendmail(EMAIL_FROM, email_to, msg.as_string())
        print("Relatório de importação enviado por e-mail.")
    except Exception as exc:
        print(f"Erro ao enviar relatório de importação: {exc}")
