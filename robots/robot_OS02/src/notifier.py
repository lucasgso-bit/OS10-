"""Send import/launch summary and error notification emails for OS02."""

from __future__ import annotations

import html
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import pyautogui

from config import COMPUTADOR_ROBO, EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST, TICKETLOG_EMAIL_TO

SCREENSHOT_DIR = r"C:\OuroSafra\IMGERRO"

EMAIL_TO = [
    "matheus.correa@ourosafra.com.br",
]

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


_HTML_ERRO = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Erro na automacao - VX360</title>
  <style>
    body { margin:0; padding:0; background-color:#f4f5f6; font-family:Arial,sans-serif; font-size:16px; color:#333333; }
    .email-wrapper { width:100%; padding:24px 0; background-color:#f4f5f6; }
    .email-container { max-width:720px; margin:0 auto; background-color:#ffffff; border-radius:12px; box-shadow:0 2px 10px rgba(0,0,0,0.08); overflow:hidden; border:1px solid #e5e5e5; }
    .email-header { background-color:#f7b500; padding:22px 26px; display:flex; justify-content:space-between; align-items:center; }
    .email-header img { max-height:64px; width:auto; display:block; }
    .header-title { color:#ffffff; font-size:16px; font-weight:bold; text-align:right; letter-spacing:0.4px; text-transform:uppercase; }
    .email-body { padding:32px 26px; }
    .status-box { background-color:#fff8e1; border-left:5px solid #f7b500; padding:16px 18px; margin-bottom:24px; border-radius:8px; }
    .status-title { margin:0 0 6px; color:#8a5a00; font-size:20px; font-weight:bold; }
    .status-text { margin:0; color:#333333; line-height:1.6; }
    .email-body h1 { font-size:22px; color:#333333; margin-top:0; margin-bottom:16px; }
    .email-body h2 { font-size:17px; color:#333333; margin-top:28px; margin-bottom:12px; border-bottom:2px solid #f7b500; padding-bottom:8px; }
    .email-body p { margin:0 0 16px; line-height:1.7; }
    .info-table { width:100%; border-collapse:collapse; margin-top:12px; margin-bottom:22px; }
    .info-table th { width:34%; text-align:left; background-color:#fafafa; color:#333333; padding:11px; border:1px solid #dddddd; font-weight:bold; }
    .info-table td { padding:11px; border:1px solid #dddddd; color:#333333; word-break:break-word; background-color:#ffffff; }
    .warning-row th { background-color:#fff8e1; color:#8a5a00; }
    .warning-row td { background-color:#fffdf2; color:#8a5a00; font-weight:bold; }
    .note-box { background-color:#f7f7f7; border-left:5px solid #333333; padding:14px 16px; margin:22px 0; border-radius:8px; color:#333333; line-height:1.6; }
    .signature { margin-top:26px; }
    .email-footer { background-color:#333333; text-align:center; padding:16px; font-size:13px; color:#ffffff; }
  </style>
</head>
<body>
  <div class="email-wrapper">
    <div class="email-container">
      <div class="email-header">
        <img src="https://www.ourosafra.com.br/wp-content/uploads/2023/11/logo_ourosafra_sem-margens.png" alt="Ouro Safra" />
        <div class="header-title">Excelência Operacional - VX360</div>
      </div>
      <div class="email-body">
        <div class="status-box">
          <p class="status-title">{{MOTIVO}}</p>
          <p class="status-text">A automação VX360 encontrou um erro e o registro abaixo não foi processado.</p>
        </div>
        <h1>Relatório de Ocorrência - VX360</h1>
        <p>Prezados,</p>
        <p>Informamos que a execução da automação foi interrompida conforme detalhes abaixo.</p>
        <h2>Status da Execução</h2>
        <table class="info-table">
          <tr class="warning-row">
            <th>Status</th>
            <td>NÃO PROCESSADO</td>
          </tr>
          <tr class="warning-row">
            <th>Motivo</th>
            <td>{{MOTIVO}}</td>
          </tr>
          <tr>
            <th>Robô</th>
            <td>OS02 — Lançamento TicketLog</td>
          </tr>
          <tr>
            <th>Usuário</th>
            <td>{{USUARIO}}</td>
          </tr>
        </table>
        <h2>Dados da Nota</h2>
        <table class="info-table">
          <tr><th>Número da Nota</th><td>{{NUMERO_NOTA}}</td></tr>
          <tr><th>Série</th><td>{{SERIE}}</td></tr>
          <tr><th>Estabelecimento</th><td>{{ESTAB}}</td></tr>
          <tr><th>Lote</th><td>{{CODIGO_LOTE}}</td></tr>
          <tr><th>Chave de Acesso</th><td>{{CHAVE_ACESSO}}</td></tr>
          <tr><th>NCM</th><td>{{NCM}}</td></tr>
          <tr><th>CFOP</th><td>{{CFOP}}</td></tr>
          <tr><th>Quantidade</th><td>{{QUANTIDADE}}</td></tr>
          <tr><th>Valor Unitário</th><td>{{VALOR_UNITARIO}}</td></tr>
        </table>
        <div class="note-box">
          <strong>Ação recomendada:</strong>
          verificar os dados informados e corrigir o registro para reprocessamento.
        </div>
        <p class="signature">Atenciosamente,</p>
        <p><strong>Excelência Operacional - VX360</strong></p>
      </div>
      <div class="email-footer">
        Este é um e-mail enviado automaticamente. Por favor, não responda.
      </div>
    </div>
  </div>
</body>
</html>
"""


def _build_html_erro(nota: dict[str, Any], motivo: str) -> str:
    usuario = os.environ.get("USERNAME") or os.environ.get("USER") or "desconhecido"
    fields = {
        "{{MOTIVO}}": html.escape(motivo),
        "{{USUARIO}}": html.escape(usuario),
        "{{NUMERO_NOTA}}": html.escape(str(nota.get("NUMERO_NOTA") or "")),
        "{{SERIE}}": html.escape(str(nota.get("SERIE") or "")),
        "{{ESTAB}}": html.escape(str(nota.get("ESTAB") or "")),
        "{{CODIGO_LOTE}}": html.escape(str(nota.get("CODIGO_LOTE") or "")),
        "{{CHAVE_ACESSO}}": html.escape(str(nota.get("CHAVE_ACESSO") or "")),
        "{{NCM}}": html.escape(str(nota.get("NCM") or "")),
        "{{CFOP}}": html.escape(str(nota.get("CFOP") or "")),
        "{{QUANTIDADE}}": html.escape(str(nota.get("QUANTIDADE") or "")),
        "{{VALOR_UNITARIO}}": html.escape(str(nota.get("VALOR_UNITARIO") or "")),
    }
    result = _HTML_ERRO
    for placeholder, value in fields.items():
        result = result.replace(placeholder, value)
    return result


def _send_error_email(nota: dict[str, Any], motivo: str, screenshot_path: str | None) -> None:
    numero_nota = nota.get("NUMERO_NOTA", "")
    estab = nota.get("ESTAB", "")
    usuario = os.environ.get("USERNAME") or os.environ.get("USER") or "desconhecido"

    msg = MIMEMultipart()
    msg["Subject"] = (
        f"VX360 OS02 - Erro | Nota {numero_nota} | Estab {estab} | Usuário {usuario}"
    )
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)
    msg.attach(MIMEText(_build_html_erro(nota, motivo), "html", "utf-8"))

    if screenshot_path and os.path.exists(screenshot_path):
        with open(screenshot_path, "rb") as f:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(screenshot_path)}"',
        )
        msg.attach(attachment)

    with smtplib.SMTP(SMTP_HOST, 25, timeout=15) as server:
        server.ehlo()
        try:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
        except smtplib.SMTPNotSupportedError:
            pass
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())


def notify_error(nota: dict[str, Any], motivo: str) -> None:
    """Take a screenshot, send an error email, then delete the screenshot."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    numero_nota = nota.get("NUMERO_NOTA", "sem_nota")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"erro_os02_{numero_nota}_{timestamp}.png")

    screenshot_saved = False
    try:
        pyautogui.screenshot(screenshot_path)
        print(f"[OS02] Screenshot salvo: {screenshot_path}")
        screenshot_saved = True
    except Exception as exc:
        print(f"[OS02] Erro ao tirar screenshot: {exc}")

    try:
        _send_error_email(nota, motivo, screenshot_path if screenshot_saved else None)
        print("[OS02] Email de erro enviado.")
    except Exception as exc:
        print(f"[OS02] Erro ao enviar email: {exc}")

    if screenshot_saved and os.path.exists(screenshot_path):
        try:
            os.remove(screenshot_path)
        except Exception:
            pass


def _build_html_conclusao(relatorio: list[dict[str, Any]], computador: str) -> str:
    total = len(relatorio)
    sucessos = sum(1 for r in relatorio if r["status"] == "OK")
    erros = total - sucessos
    taxa = round(sucessos / total * 100, 1) if total else 0.0

    nota_rows = ""
    for r in relatorio:
        is_ok = r["status"] == "OK"
        cor_status = "#2e7d32" if is_ok else "#c62828"
        status_texto = "LANÇADO" if is_ok else "ERRO"
        motivo = "" if is_ok else html.escape(str(r.get("motivo") or ""))
        nota_rows += (
            f"<tr>"
            f"<td style='{_TD}'>{html.escape(str(r.get('nota', '')))}</td>"
            f"<td style='{_TD}'>{html.escape(str(r.get('estab', '')))}</td>"
            f"<td style='{_TD}'>{html.escape(str(r.get('lote', '')))}</td>"
            f"<td style='{_TD};color:{cor_status};font-weight:bold'>{status_texto}</td>"
            f"<td style='{_TD}'>{motivo}</td>"
            f"</tr>"
        )

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
    <h1 style="font-size:22px;margin:0 0 6px">Relatório Final de Execução - OS02</h1>
    <p style="margin:0 0 20px;color:#666">
      Máquina: <strong>{computador}</strong>
      &nbsp;|&nbsp;
      Data: <strong>{datetime.now().strftime('%d/%m/%Y %H:%M')}</strong>
    </p>
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px">
      {_card(total,    "Total",    "#e3f2fd", "#1976d2")}
      {_card(sucessos, "Lançadas", "#e8f5e9", "#388e3c")}
      {_card(erros,    "Erros",    "#fff3e0", "#e65100")}
    </div>
    <div style="background:#fff8e1;border-left:5px solid #f7b500;
                padding:14px 16px;border-radius:8px;margin-bottom:20px">
      Taxa de sucesso: <strong>{taxa}%</strong>
    </div>
    <h2 style="font-size:17px;color:#333;border-bottom:2px solid #f7b500;padding-bottom:8px;margin-top:28px">
      Detalhamento por Nota
    </h2>
    <table style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr>
        <th style="{_TH}">Nota</th>
        <th style="{_TH}">Estab</th>
        <th style="{_TH}">Lote</th>
        <th style="{_TH}">Status</th>
        <th style="{_TH}">Motivo</th>
      </tr>
      {nota_rows}
    </table>
  </div>
  <div style="background:#333;color:#fff;text-align:center;padding:14px;font-size:12px">
    Este é um e-mail enviado automaticamente. Por favor, não responda.
  </div>
</div>
</body></html>"""


def notify_conclusao(relatorio: list[dict[str, Any]]) -> None:
    """Send Phase-1 completion summary email — mirrors OS07 enviar_relatorio_final."""
    try:
        total = len(relatorio)
        sucessos = sum(1 for r in relatorio if r["status"] == "OK")
        erros = total - sucessos

        html_body = _build_html_conclusao(relatorio, COMPUTADOR_ROBO)

        msg = MIMEMultipart()
        msg["Subject"] = (
            f"VX360 OS02 — Relatório Final | {COMPUTADOR_ROBO} | "
            f"Total: {total} | Lançadas: {sucessos} | Erro: {erros}"
        )
        msg["From"] = EMAIL_FROM
        msg["To"] = ", ".join(EMAIL_TO)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, 25, timeout=15) as server:
            server.ehlo()
            try:
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
            except smtplib.SMTPNotSupportedError:
                pass
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print("[OS02] Relatório final enviado por e-mail.")
    except Exception as exc:
        print(f"[OS02] Erro ao enviar relatório final: {exc}")
