"""Send error notifications for the financial robot.

Capture screenshots and send SMTP email alerts when handled errors occur.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-06-01
Version: 1.0.0
"""

from __future__ import annotations

import smtplib
from datetime import datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path

import pyautogui

from config import EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST, OS18_SMTP_TO

SMTP_FROM = EMAIL_FROM
SMTP_PASSWORD = EMAIL_PASSWORD
SMTP_TO = OS18_SMTP_TO
SMTP_PORT = 25
SMTP_USE_TLS = False
SMTP_USER = ""

ERROR_SCREENSHOT_DIR = Path("logs") / "prints_erros"


def capture_error_screenshot(
    error_name: str,
    fornecedor: str = "",
    empresa: str = "",
) -> Path:
    """Capture the current screen before closing an error popup."""
    ERROR_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    safe_error_name = (
        error_name.replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    file_name = (
        f"{timestamp}_EMPRESA_{empresa}_"
        f"FORNECEDOR_{fornecedor}_{safe_error_name}.png"
    )

    screenshot_path = ERROR_SCREENSHOT_DIR / file_name

    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)

    print(f"Print do erro salvo em: {screenshot_path}")

    return screenshot_path


def build_error_email_html(
    error_name: str,
    error_description: str,
    fornecedor: str = "",
    empresa: str = "",
    data_hora: str = "",
) -> str:
    """Build the HTML body for robot error notification emails."""
    error_name = escape(str(error_name))
    error_description = escape(str(error_description))
    fornecedor = escape(str(fornecedor))
    empresa = escape(str(empresa))
    data_hora = escape(str(data_hora))

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Erro no Robô Financeiro</title>

  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #f4f5f6;
      font-family: Arial, sans-serif;
      font-size: 16px;
      color: #333333;
    }}

    .email-wrapper {{
      width: 100%;
      padding: 24px 0;
      background-color: #f4f5f6;
    }}

    .email-container {{
      max-width: 720px;
      margin: 0 auto;
      background-color: #ffffff;
      border-radius: 12px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
      overflow: hidden;
      border: 1px solid #e5e5e5;
    }}

    .email-header {{
      background-color: #b42318;
      padding: 22px 26px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .email-header img {{
      max-height: 64px;
      width: auto;
      display: block;
    }}

    .header-title {{
      color: #ffffff;
      font-size: 16px;
      font-weight: bold;
      text-align: right;
      letter-spacing: 0.4px;
      text-transform: uppercase;
    }}

    .email-body {{
      padding: 32px 26px;
    }}

    .status-box {{
      background-color: #fff1f0;
      border-left: 5px solid #b42318;
      padding: 16px 18px;
      margin-bottom: 24px;
      border-radius: 8px;
    }}

    .status-title {{
      margin: 0 0 6px;
      color: #912018;
      font-size: 20px;
      font-weight: bold;
    }}

    .status-text {{
      margin: 0;
      color: #333333;
      line-height: 1.6;
    }}

    .email-body h1 {{
      font-size: 22px;
      color: #333333;
      margin-top: 0;
      margin-bottom: 16px;
      text-transform: uppercase;
    }}

    .email-body h2 {{
      font-size: 17px;
      color: #333333;
      margin-top: 28px;
      margin-bottom: 12px;
      border-bottom: 2px solid #b42318;
      padding-bottom: 8px;
    }}

    .email-body p {{
      margin: 0 0 16px;
      line-height: 1.7;
    }}

    .info-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      margin-bottom: 22px;
    }}

    .info-table th {{
      width: 34%;
      text-align: left;
      background-color: #fafafa;
      color: #333333;
      padding: 11px;
      border: 1px solid #dddddd;
      font-weight: bold;
    }}

    .info-table td {{
      padding: 11px;
      border: 1px solid #dddddd;
      color: #333333;
      word-break: break-word;
      background-color: #ffffff;
    }}

    .error-row th {{
      background-color: #fff1f0;
      color: #912018;
    }}

    .error-row td {{
      background-color: #fff7f7;
      color: #912018;
      font-weight: bold;
    }}

    .note-box {{
      background-color: #f7f7f7;
      border-left: 5px solid #333333;
      padding: 14px 16px;
      margin: 22px 0;
      border-radius: 8px;
      color: #333333;
      line-height: 1.6;
    }}

    .signature {{
      margin-top: 26px;
    }}

    .signature strong {{
      color: #333333;
    }}

    .email-footer {{
      background-color: #333333;
      text-align: center;
      padding: 16px;
      font-size: 13px;
      color: #ffffff;
    }}
  </style>
</head>

<body>
  <div class="email-wrapper">
    <div class="email-container">

      <div class="email-header">
        <img
          src="https://www.ourosafra.com.br/wp-content/uploads/2023/11/logo_ourosafra_sem-margens.png"
          alt="Ouro Safra"
        />
        <div class="header-title">Robô Financeiro</div>
      </div>

      <div class="email-body">
        <div class="status-box">
          <p class="status-title">Erro identificado durante a automação</p>
          <p class="status-text">
            O robô financeiro encontrou uma tela de erro ou atenção durante o processamento.
            O fornecedor abaixo foi interrompido ou exigiu tratamento automático.
          </p>
        </div>

        <h1>Erro no Robô Financeiro</h1>

        <p>Prezados,</p>

        <p>
          Informamos que ocorreu uma inconsistência durante a execução do robô financeiro.
          Seguem abaixo os dados identificados no momento do erro.
        </p>

        <h2>Status da Execução</h2>

        <table class="info-table">
          <tr class="error-row">
            <th>Status</th>
            <td>ERRO / ATENÇÃO</td>
          </tr>
          <tr class="error-row">
            <th>Processo</th>
            <td>Robô Financeiro - Processamento de Fornecedor</td>
          </tr>
        </table>

        <h2>Dados do Processamento</h2>

        <table class="info-table">
          <tr>
            <th>Empresa / Estab</th>
            <td>{empresa}</td>
          </tr>
          <tr>
            <th>Fornecedor</th>
            <td>{fornecedor}</td>
          </tr>
          <tr>
            <th>Erro</th>
            <td>{error_name}</td>
          </tr>
          <tr>
            <th>Descrição</th>
            <td>{error_description}</td>
          </tr>
          <tr>
            <th>Data/Hora</th>
            <td>{data_hora}</td>
          </tr>
        </table>

        <div class="note-box">
          <strong>Ação recomendada:</strong>
          verificar o fornecedor e a tela capturada em anexo antes de realizar novo processamento.
        </div>

        <p>
          O print da tela no momento do erro foi anexado a este e-mail.
        </p>

        <p class="signature">Atenciosamente,</p>

        <p>
          <strong>Excelência Operacional - Robô Financeiro</strong>
        </p>
      </div>

      <div class="email-footer">
        Este é um e-mail enviado automaticamente. Por favor, não responda.
      </div>

    </div>
  </div>
</body>
</html>
"""


def send_error_email(
    subject: str,
    body: str,
    attachment_path: Path,
    html_body: str | None = None,
) -> bool:
    """Send an error email with a screenshot attachment using SMTP."""
    try:
        message = EmailMessage()
        message["From"] = SMTP_FROM
        message["To"] = SMTP_TO
        message["Subject"] = subject

        message.set_content(body)

        if html_body:
            message.add_alternative(html_body, subtype="html")

        with attachment_path.open("rb") as file:
            message.add_attachment(
                file.read(),
                maintype="image",
                subtype="png",
                filename=attachment_path.name,
            )

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            if SMTP_USE_TLS:
                server.starttls()

            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)

            server.send_message(message)

        print("E-mail de erro enviado com sucesso.")
        return True

    except Exception as error:
        print(f"Falha ao enviar e-mail de erro: {error}")
        return False


def notify_error_before_close(
    error_name: str,
    error_description: str,
    fornecedor: str = "",
    empresa: str = "",
) -> None:
    """Capture and send an error notification before closing the popup."""
    try:
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        screenshot_path = capture_error_screenshot(
            error_name=error_name,
            fornecedor=fornecedor,
            empresa=empresa,
        )

        subject = f"Erro Robô Financeiro - {error_name}"

        body = (
            "O robô encontrou uma tela de erro/atenção durante o processamento.\n\n"
            f"Erro: {error_name}\n"
            f"Descrição: {error_description}\n"
            f"Empresa/Estab: {empresa}\n"
            f"Fornecedor: {fornecedor}\n"
            f"Data/Hora: {data_hora}\n\n"
            "Print da tela em anexo."
        )

        html_body = build_error_email_html(
            error_name=error_name,
            error_description=error_description,
            fornecedor=fornecedor,
            empresa=empresa,
            data_hora=data_hora,
        )

        send_error_email(
            subject=subject,
            body=body,
            attachment_path=screenshot_path,
            html_body=html_body,
        )

    except Exception as error:
        print(f"Falha ao gerar notificação de erro: {error}")
