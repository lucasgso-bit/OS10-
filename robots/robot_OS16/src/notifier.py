"""Send error notification emails for failed note processing.

Screenshot → email with attachment → delete screenshot.

Developed by: Matheus Correa
Updated by: Matheus Correa
Last Modified: 2026-06-08
Version: 1.0.0
"""

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

from config import EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST

SCREENSHOT_DIR = r"C:\Users\rpa.dev1\Downloads\screen"
EMAIL_TO = [
    "matheus.correa@ourosafra.com.br",
    "nfe.cereais@ourosafra.com.br",
    "alif.toledo@ourosafra.com.br",
    "isaque.ricardo@ourosafra.com.br",
    "hugo.arantes@ourosafra.com.br",
]

_HTML_TEMPLATE = """\
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
            <th>Configuração</th>
            <td>{{NOTACONF}}</td>
          </tr>
        </table>
        <h2>Dados do Documento</h2>
        <table class="info-table">
          <tr><th>Placa</th><td>{{PLACA}}</td></tr>
          <tr><th>Número da Ordem</th><td>{{ORDEMCARGA}}</td></tr>
          <tr><th>Número da Nota</th><td>{{NUMERONOTA}}</td></tr>
          <tr><th>Estabelecimento</th><td>{{ESTAB}}</td></tr>
          <tr><th>Chave</th><td>{{CHAVEACESSO}}</td></tr>
          <tr><th>Número CM</th><td>{{NUMEROCM}}</td></tr>
          <tr><th>Quantidade</th><td>{{QUANTIDADE}}</td></tr>
        </table>
        <h2>Dados da Pessoa</h2>
        <table class="info-table">
          <tr><th>Inscrição Pessoa</th><td>{{IEEMITENTE}}</td></tr>
          <tr><th>Pessoa</th><td>{{PRODUTOR}}</td></tr>
          <tr><th>Classificação</th><td>{{CLASSIF_LOCAL}}</td></tr>
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


def _build_html(nota: dict[str, Any], motivo: str) -> str:
    fields = {
        "{{MOTIVO}}": html.escape(motivo),
        "{{NOTACONF}}": html.escape(str(nota.get("NOTACONF") or "")),
        "{{PLACA}}": html.escape(str(nota.get("PLACA") or "")),
        "{{ORDEMCARGA}}": html.escape(str(nota.get("ORDEMCARGA") or "")),
        "{{NUMERONOTA}}": html.escape(str(nota.get("NUMERONOTA") or "")),
        "{{ESTAB}}": html.escape(str(nota.get("ESTAB") or "")),
        "{{CHAVEACESSO}}": html.escape(str(nota.get("CHAVEACESSO") or "")),
        "{{NUMEROCM}}": html.escape(str(nota.get("NUMEROCM") or "")),
        "{{QUANTIDADE}}": html.escape(str(nota.get("QUANTIDADE") or "")),
        "{{IEEMITENTE}}": html.escape(str(nota.get("IEEMITENTE") or "")),
        "{{PRODUTOR}}": html.escape(str(nota.get("PRODUTOR") or "")),
        "{{CLASSIF_LOCAL}}": html.escape(str(nota.get("CLASSIF_LOCAL") or "")),
    }
    result = _HTML_TEMPLATE
    for placeholder, value in fields.items():
        result = result.replace(placeholder, value)
    return result


def _send_email(nota: dict[str, Any], motivo: str, screenshot_path: str | None) -> None:
    notaconf = nota.get("NOTACONF", "")
    estab = nota.get("ESTAB", "")
    nota_id = nota.get("U_FISCAL_IO_CONT_ID", "")

    msg = MIMEMultipart()
    msg["Subject"] = (
        f"VX360 - Erro | NOTACONF {notaconf} | Estab {estab} | ID {nota_id}"
    )
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    msg.attach(MIMEText(_build_html(nota, motivo), "html", "utf-8"))

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
    """Take screenshot, send error email, then delete the screenshot."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    nota_id = nota.get("U_FISCAL_IO_CONT_ID", "sem_id")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"erro_{nota_id}_{timestamp}.png")

    screenshot_saved = False
    try:
        pyautogui.screenshot(screenshot_path)
        print(f"Screenshot salvo: {screenshot_path}")
        screenshot_saved = True
    except Exception as exc:
        print(f"Erro ao tirar screenshot: {exc}")

    try:
        _send_email(nota, motivo, screenshot_path if screenshot_saved else None)
        print("Email de erro enviado.")
    except Exception as exc:
        print(f"Erro ao enviar email: {exc}")

    if screenshot_saved and os.path.exists(screenshot_path):
        try:
            os.remove(screenshot_path)
            print("Screenshot deletado.")
        except Exception as exc:
            print(f"Erro ao deletar screenshot: {exc}")
