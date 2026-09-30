"""OS10 email notification module.

Send OS10 execution summary and error emails.

Developed by: João Netto
Updated by: João Netto
Last Modified: 2026-07-08
Version: 1.0.1
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

from config import (
    COMPUTADOR_ROBO,
    EMAIL_FROM,
    EMAIL_PASSWORD,
    SMTP_HOST,
)

EMAIL_TO = [
    "joao.netto@ourosafra.com.br",
    "lucas.oliveira@ourosafra.com.br"
]

_TH = (
    "background:#fafafa;padding:9px 10px;text-align:left;"
    "border:1px solid #ddd;font-size:13px"
)
_TD = "padding:8px 10px;border:1px solid #ddd;font-size:13px"


def _get_value(data: dict[str, Any], *keys: str, default: str = "") -> str:
    """Return first non-empty value from dict."""
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    return default


def _is_success(row: dict[str, Any]) -> bool:
    """Check if report row is successful based on message."""
    mensagem = _get_value(row, "Mensagem", "mensagem").upper()
    return not mensagem.startswith("ERRO")


def _card(valor: int | str, label: str, bg: str, border: str) -> str:
    """Build a summary card."""
    return (
        f'<div style="flex:1;min-width:120px;border-radius:8px;padding:14px 12px;'
        f'text-align:center;background:{bg};border-left:5px solid {border}">'
        f'<p style="font-size:28px;font-weight:bold;margin:0">{valor}</p>'
        f'<p style="font-size:12px;color:#555;margin:4px 0 0">{label}</p></div>'
    )


def _build_html_conclusao_os10(
    relatorio: list[dict[str, Any]],
    computador: str,
) -> str:
    """Build OS10 final execution report HTML."""
    total = len(relatorio)
    sucessos = sum(1 for row in relatorio if _is_success(row))
    erros = total - sucessos
    taxa = round(sucessos / total * 100, 1) if total else 0.0

    rows = ""

    for row in relatorio:
        mensagem = _get_value(row, "Mensagem", "mensagem")
        is_ok = _is_success(row)
        cor_mensagem = "#2e7d32" if is_ok else "#c62828"

        estab = _get_value(row, "Estab", "estab", "ESTAB")
        cnpj_fornecedor = _get_value(
            row,
            "CNPJ Fornecedor",
            "cnpj_fornecedor",
            "CNPJF_FORNECEDOR",
            "CNPJ_PED",
            "EMITENTE_CNPJ",
            "CNPJ",
        )
        num_pedido = _get_value(row, "NumPedido", "num_pedido", "NUM_PED", "PEDIDO")
        data_emissao = _get_value(
            row,
            "Data_Emissao",
            "Data Emissao",
            "data_emissao",
            "DTEMISSAO",
        )

        rows += (
            "<tr>"
            f"<td style='{_TD}'>{html.escape(estab)}</td>"
            f"<td style='{_TD}'>{html.escape(cnpj_fornecedor)}</td>"
            f"<td style='{_TD}'>{html.escape(num_pedido)}</td>"
            f"<td style='{_TD}'>{html.escape(data_emissao)}</td>"
            f"<td style='{_TD};color:{cor_mensagem};font-weight:bold'>"
            f"{html.escape(mensagem)}</td>"
            "</tr>"
        )

    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f4f5f6;font-family:Arial,sans-serif;font-size:15px;color:#333">
<div style="max-width:860px;margin:24px auto;background:#fff;border-radius:12px;
            border:1px solid #e5e5e5;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08)">
  <div style="background:#f7b500;padding:20px 26px;display:flex;
              justify-content:space-between;align-items:center">
    <img src="https://siteos.blob.core.windows.net/corp/DOCLogoOuro.png"
         alt="Ouro Safra" style="max-height:56px"/>
    <span style="color:#fff;font-size:15px;font-weight:bold;text-transform:uppercase;
                 letter-spacing:.4px">Excelência Operacional - VX360</span>
  </div>

  <div style="padding:30px 26px">
    <h1 style="font-size:22px;margin:0 0 6px">Relatório Final de Execução - OS10</h1>

    <p style="margin:0 0 20px;color:#666">
      Máquina: <strong>{html.escape(str(computador))}</strong>
      &nbsp;|&nbsp;
      Data: <strong>{datetime.now().strftime('%d/%m/%Y %H:%M')}</strong>
    </p>

    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px">
      {_card(total, "Total", "#e3f2fd", "#1976d2")}
      {_card(sucessos, "Preparadas", "#e8f5e9", "#388e3c")}
      {_card(erros, "Erros", "#fff3e0", "#e65100")}
    </div>

    <div style="background:#fff8e1;border-left:5px solid #f7b500;
                padding:14px 16px;border-radius:8px;margin-bottom:20px">
      Taxa de sucesso: <strong>{taxa}%</strong>
    </div>

    <h2 style="font-size:17px;color:#333;border-bottom:2px solid #f7b500;padding-bottom:8px;margin-top:28px">
      Detalhamento da Execução
    </h2>

    <table style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr>
        <th style="{_TH}">Estab</th>
        <th style="{_TH}">CNPJ Fornecedor</th>
        <th style="{_TH}">NumPedido</th>
        <th style="{_TH}">Data_Emissao</th>
        <th style="{_TH}">Mensagem</th>
      </tr>
      {rows}
    </table>
  </div>

  <div style="background:#333;color:#fff;text-align:center;padding:14px;font-size:12px">
    Este é um e-mail enviado automaticamente. Por favor, não responda.
  </div>
</div>
</body></html>"""


def notify_conclusao_os10(relatorio: list[dict[str, Any]]) -> None:
    """Send OS10 final execution summary email."""
    try:
        total = len(relatorio)
        sucessos = sum(1 for row in relatorio if _is_success(row))
        erros = total - sucessos

        html_body = _build_html_conclusao_os10(relatorio, COMPUTADOR_ROBO)

        msg = MIMEMultipart()
        msg["Subject"] = (
            f"OS10 NFSE — Relatório Final | "
            f"Total: {total} | Preparadas: {sucessos} | Erro: {erros}"
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

        print("[OS10] Relatório final enviado por e-mail.")

    except Exception as exc:
        print(f"[OS10] Erro ao enviar relatório final: {exc}")


def notify_erro_os10(
    nota: dict[str, Any],
    motivo: str,
    screenshot_path: str | None = None,
) -> None:
    """Send OS10 error email with optional screenshot."""
    try:
        estabelecimento = _get_value(
            nota, "Estabelecimento", "Estab", "ESTAB", default="79"
        )
        numero_nota = _get_value(
            nota,
            "Número da nota",
            "Numero da nota",
            "NUMERO_NF",
            "NUMERO_NOTA",
            "NOTA",
            "NOTATERC",
        )
        pedido = _get_value(nota, "Pedido", "NumPedido", "NUM_PED", "PEDIDO")
        valor = _get_value(
            nota,
            "Valor",
            "VALOR_TOTAL_NF",
            "VALORTOTAL",
            "VALOR_LIQUIDO",
        )
        data_emissao = _get_value(
            nota,
            "Data Emissao",
            "Data_Emissao",
            "DTEMISSAO",
            "DATA_EMISSAO",
        )
        cnpj_fornecedor = _get_value(
            nota,
            "CNPJ Fornecedor",
            "CNPJF_FORNECEDOR",
            "CNPJ_PED",
            "EMITENTE_CNPJ",
            "CNPJ",
        )

        html_body = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f4f5f6;font-family:Arial,sans-serif;font-size:15px;color:#333">
<div style="max-width:760px;margin:24px auto;background:#fff;border-radius:12px;
            border:1px solid #e5e5e5;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08)">
  <div style="background:#c62828;padding:20px 26px;color:#fff;font-weight:bold">
    OS10 NFSE — Erro na Execução
  </div>

  <div style="padding:30px 26px">
    <h1 style="font-size:22px;margin:0 0 16px">Erro durante preparação da Nota Fiscal</h1>

    <p style="margin:0 0 20px;color:#666">
      Máquina: <strong>{html.escape(str(COMPUTADOR_ROBO))}</strong>
      &nbsp;|&nbsp;
      Data: <strong>{datetime.now().strftime('%d/%m/%Y %H:%M')}</strong>
    </p>

    <div style="background:#ffebee;border-left:5px solid #c62828;
                padding:14px 16px;border-radius:8px;margin-bottom:20px">
      <strong>Motivo:</strong> {html.escape(str(motivo))}
    </div>

    <table style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr><th style="{_TH}">Estabelecimento</th><td style="{_TD}">{html.escape(estabelecimento)}</td></tr>
      <tr><th style="{_TH}">Número da nota</th><td style="{_TD}">{html.escape(numero_nota)}</td></tr>
      <tr><th style="{_TH}">Pedido</th><td style="{_TD}">{html.escape(pedido)}</td></tr>
      <tr><th style="{_TH}">Valor</th><td style="{_TD}">{html.escape(valor)}</td></tr>
      <tr><th style="{_TH}">Data Emissao</th><td style="{_TD}">{html.escape(data_emissao)}</td></tr>
      <tr><th style="{_TH}">CNPJ Fornecedor</th><td style="{_TD}">{html.escape(cnpj_fornecedor)}</td></tr>
    </table>

    <p style="margin-top:18px;color:#666">
      O robô registrou a ocorrência e anexou o print da tela, quando disponível.
    </p>
  </div>

  <div style="background:#333;color:#fff;text-align:center;padding:14px;font-size:12px">
    Este é um e-mail enviado automaticamente. Por favor, não responda.
  </div>
</div>
</body></html>"""

        msg = MIMEMultipart()
        msg["Subject"] = (
            f"OS10 NFSE — Erro na Execução | "
            f"Pedido {pedido or '-'} | Nota {numero_nota or '-'} | {COMPUTADOR_ROBO}"
        )
        msg["From"] = EMAIL_FROM
        msg["To"] = ", ".join(EMAIL_TO)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, "rb") as file:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(file.read())

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

        print("[OS10] E-mail de erro enviado.")

    except Exception as exc:
        print(f"[OS10] Erro ao enviar e-mail de erro: {exc}")


# Aliases temporários para não quebrar imports antigos.
# Pode remover depois que o lancamento.py importar notify_conclusao_os10 e notify_erro_os10.
notify_conclusao_os03 = notify_conclusao_os10
notify_erro_os03 = notify_erro_os10
