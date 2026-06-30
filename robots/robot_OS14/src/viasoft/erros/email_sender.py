from __future__ import annotations

import html
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import pyautogui

from config import EMAIL_FROM, EMAIL_PASSWORD, OS14_EMAIL_TO, SMTP_HOST, SMTP_PORT


SCREENSHOT_DIR = Path("logs/screenshots")

LOGO_URL = "https://www.ourosafra.com.br/images/LogoOuro.png"


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Erro na automação - OS14 NOTA_ACERTO</title>
  <style>
    body { margin:0;padding:0;background-color:#f4f5f6;font-family:Arial,sans-serif;font-size:16px;color:#333; }
    .email-wrapper { width:100%;padding:24px 0;background-color:#f4f5f6; }
    .email-container { max-width:760px;margin:0 auto;background-color:#fff;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08);overflow:hidden;border:1px solid #e5e5e5; }
    .email-header { background-color:#000;padding:22px 26px;display:flex;justify-content:space-between;align-items:center; }
    .email-header img { max-height:64px;width:auto;display:block; }
    .header-title { color:#fff;font-size:16px;font-weight:bold;text-align:right;letter-spacing:.4px;text-transform:uppercase; }
    .email-body { padding:32px 26px; }
    .status-box { background-color:#fff8e1;border-left:5px solid #f7b500;padding:16px 18px;margin-bottom:24px;border-radius:8px; }
    .status-title { margin:0 0 6px;color:#8a5a00;font-size:20px;font-weight:bold; }
    .status-text { margin:0;color:#333;line-height:1.6; }
    h1 { font-size:22px;color:#333;margin-top:0;margin-bottom:16px; }
    h2 { font-size:17px;color:#333;margin-top:28px;margin-bottom:12px;border-bottom:2px solid #f7b500;padding-bottom:8px; }
    p { margin:0 0 16px;line-height:1.7; }
    .info-table { width:100%;border-collapse:collapse;margin-top:12px;margin-bottom:22px; }
    .info-table th { width:34%;text-align:left;background-color:#fafafa;color:#333;padding:11px;border:1px solid #ddd;font-weight:bold; }
    .info-table td { padding:11px;border:1px solid #ddd;color:#333;word-break:break-word;background-color:#fff; }
    .warning-row th { background-color:#fff8e1;color:#8a5a00; }
    .warning-row td { background-color:#fffdf2;color:#8a5a00;font-weight:bold; }
    .note-box { background-color:#f7f7f7;border-left:5px solid #333;padding:14px 16px;margin:22px 0;border-radius:8px;color:#333;line-height:1.6; }
    .email-footer { background-color:#333;text-align:center;padding:16px;font-size:13px;color:#fff; }
  </style>
</head>
<body>
  <div class="email-wrapper"><div class="email-container">
    <div class="email-header">
      <img src="{{LOGO_URL}}" alt="Ouro Safra" />
      <div class="header-title">Excelência Operacional - OS14</div>
    </div>
    <div class="email-body">
      <div class="status-box">
        <p class="status-title">{{MOTIVO}}</p>
        <p class="status-text">A automação OS14 - NOTA_ACERTO encontrou um erro e o pedido abaixo não foi processado.</p>
      </div>
      <h1>Relatório de Ocorrência - OS14 NOTA_ACERTO</h1>
      <p>Prezados,</p>
      <p>Informamos que a execução da automação identificou uma falha durante o processamento do pedido abaixo.</p>
      <h2>Status da Execução</h2>
      <table class="info-table">
        <tr class="warning-row"><th>Status</th><td>NÃO PROCESSADO</td></tr>
        <tr class="warning-row"><th>Motivo</th><td>{{MOTIVO}}</td></tr>
        <tr><th>Data/Hora</th><td>{{DATA_HORA}}</td></tr>
        <tr><th>Regra NOTACONF</th><td>{{REGRA_NOTACONF}}</td></tr>
      </table>
      <h2>Dados do Pedido</h2>
      <table class="info-table">
        <tr><th>Estabelecimento</th><td>{{ESTAB}}</td></tr>
        <tr><th>Número do Pedido</th><td>{{NUM_PED}}</td></tr>
        <tr><th>Fornecedor</th><td>{{FORNECEDOR}}</td></tr>
        <tr><th>CNPJ Fornecedor</th><td>{{CNPJF_FORNECEDOR}}</td></tr>
        <tr><th>IE Fornecedor</th><td>{{IE_FORNECEDOR}}</td></tr>
        <tr><th>Tipo de Pagamento</th><td>{{TIPOPGTO}}</td></tr>
        <tr><th>Valor Total</th><td>{{VALORTOTAL}}</td></tr>
      </table>
      <h2>Dados da Nota</h2>
      <table class="info-table">
        <tr><th>Chave NF</th><td>{{CHAVCHAVENF}}</td></tr>
        <tr><th>Chave Boleto</th><td>{{CHAVEBOLETO}}</td></tr>
        <tr><th>Banco</th><td>{{BANCO}}</td></tr>
        <tr><th>Agência</th><td>{{AGENCIA}}</td></tr>
        <tr><th>Conta</th><td>{{CONTA}}</td></tr>
        <tr><th>PIX</th><td>{{PIX}}</td></tr>
      </table>
      <div class="note-box"><strong>Ação recomendada:</strong> verificar a evidência anexada, corrigir o pedido se necessário e liberar o reprocessamento.</div>
      <p>Atenciosamente,</p><p><strong>Excelência Operacional - OS14</strong></p>
    </div>
    <div class="email-footer">Este é um e-mail enviado automaticamente. Por favor, não responda.</div>
  </div></div>
</body>
</html>
"""


def _obter_destinatarios() -> list[str]:
    return [e.strip() for e in OS14_EMAIL_TO.split(",") if e.strip()]


def _obter_valor(pedido: dict[str, Any], chave: str) -> str:
    return html.escape(str(pedido.get(chave) or ""))


def _validar_configuracao_email() -> None:
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST não configurado no ambiente.")
    if not EMAIL_FROM:
        raise RuntimeError("EMAIL_FROM não configurado no ambiente.")
    if not _obter_destinatarios():
        raise RuntimeError("OS14_EMAIL_TO não configurado no ambiente.")


def _build_html(pedido: dict[str, Any], motivo: str) -> str:
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    fields = {
        "{{LOGO_URL}}": html.escape(LOGO_URL),
        "{{MOTIVO}}": html.escape(motivo),
        "{{DATA_HORA}}": html.escape(data_hora),
        "{{REGRA_NOTACONF}}": _obter_valor(pedido, "regra_notaconf"),
        "{{ESTAB}}": _obter_valor(pedido, "estab"),
        "{{NUM_PED}}": _obter_valor(pedido, "num_ped"),
        "{{FORNECEDOR}}": _obter_valor(pedido, "fornecedor"),
        "{{CNPJF_FORNECEDOR}}": _obter_valor(pedido, "cnpjf_fornecedor"),
        "{{IE_FORNECEDOR}}": _obter_valor(pedido, "ie_fornecedor"),
        "{{TIPOPGTO}}": _obter_valor(pedido, "tipopgto"),
        "{{VALORTOTAL}}": _obter_valor(pedido, "valortotal"),
        "{{CHAVCHAVENF}}": _obter_valor(pedido, "chavchavenf"),
        "{{CHAVEBOLETO}}": _obter_valor(pedido, "chaveboleto"),
        "{{BANCO}}": _obter_valor(pedido, "banco"),
        "{{AGENCIA}}": _obter_valor(pedido, "agencia"),
        "{{CONTA}}": _obter_valor(pedido, "conta"),
        "{{PIX}}": _obter_valor(pedido, "pix"),
    }

    result = _HTML_TEMPLATE
    for placeholder, value in fields.items():
        result = result.replace(placeholder, value)
    return result


def _anexar_arquivo(msg: MIMEMultipart, caminho_arquivo: Path) -> None:
    with caminho_arquivo.open("rb") as arquivo:
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(arquivo.read())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        f'attachment; filename="{caminho_arquivo.name}"',
    )
    msg.attach(attachment)


def _send_email(
    pedido: dict[str, Any],
    motivo: str,
    screenshot_path: str | Path | None = None,
) -> None:
    _validar_configuracao_email()

    destinatarios = _obter_destinatarios()
    regra = pedido.get("regra_notaconf", "")
    estab = pedido.get("estab", "")
    num_ped = pedido.get("num_ped", "")

    msg = MIMEMultipart()
    msg["Subject"] = f"OS14 - Erro | Regra {regra} | Estab {estab} | Pedido {num_ped}"
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(destinatarios)

    msg.attach(MIMEText(_build_html(pedido, motivo), "html", "utf-8"))

    if screenshot_path:
        caminho = Path(screenshot_path)
        if caminho.exists():
            _anexar_arquivo(msg, caminho)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.ehlo()
        if EMAIL_PASSWORD:
            try:
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
            except smtplib.SMTPNotSupportedError:
                pass
        server.sendmail(EMAIL_FROM, destinatarios, msg.as_string())


def tirar_screenshot_erro(pedido: dict[str, Any]) -> Path | None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    estab = str(pedido.get("estab", "sem_estab")).strip()
    num_ped = str(pedido.get("num_ped", "sem_pedido")).strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    nome_arquivo = f"erro_os14_estab_{estab}_pedido_{num_ped}_{timestamp}.png"
    screenshot_path = SCREENSHOT_DIR / nome_arquivo

    try:
        pyautogui.screenshot(str(screenshot_path))
        print(f"Screenshot salvo: {screenshot_path}")
        return screenshot_path
    except Exception as erro:
        print(f"Erro ao tirar screenshot: {erro}")
        return None


def notificar_erro_pedido(
    pedido: dict[str, Any],
    motivo: str,
    screenshot_path: str | Path | None = None,
    tirar_screenshot: bool = False,
) -> None:
    caminho_screenshot = Path(screenshot_path) if screenshot_path else None

    if tirar_screenshot and caminho_screenshot is None:
        caminho_screenshot = tirar_screenshot_erro(pedido)

    try:
        _send_email(pedido=pedido, motivo=motivo, screenshot_path=caminho_screenshot)
        print("E-mail de erro enviado.")
    except Exception as erro:
        print(f"Erro ao enviar e-mail de erro: {erro}")
