"""Shared email utility for the orchestration platform.

All outbound emails (alerts, reports) should go through enviar_email so that
SMTP configuration is defined in a single place.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Sequence

from config import EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST

logger = logging.getLogger(__name__)

_ALERTA_EMAIL_TO = ["matheus.correa@ourosafra.com.br"]


def enviar_email(para: Sequence[str], assunto: str, html: str) -> None:
    """Send an HTML email via the configured SMTP server."""
    msg = MIMEMultipart()
    msg["Subject"] = assunto
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(para)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, 25, timeout=15) as server:
        server.ehlo()
        try:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
        except smtplib.SMTPNotSupportedError:
            pass
        server.sendmail(EMAIL_FROM, list(para), msg.as_string())

    logger.info("Email enviado para %s | %s", list(para), assunto)


def enviar_alerta_maquinas_paradas(maquinas: list[str]) -> None:
    """Send an idle-machine alert to the operations team.

    Called when a worker machine has not sent a heartbeat for 30+ minutes.
    `maquinas` is the list of COMPUTADOR_ROBO identifiers (OS usernames).
    """
    if not maquinas:
        return

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    lista_html = "".join(
        f'<li style="margin-bottom:6px"><strong>{m}</strong></li>' for m in maquinas
    )

    html = f"""\
<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;margin:0;padding:0;background:#f5f5f5">
<div style="max-width:620px;margin:24px auto;background:#fff;border-radius:10px;
            box-shadow:0 2px 8px rgba(0,0,0,.12);overflow:hidden">

  <div style="background:#b71c1c;padding:22px 28px">
    <h2 style="color:#fff;margin:0;font-size:20px">
      &#9888; VX360 — Alerta: Máquina(s) Parada(s)
    </h2>
  </div>

  <div style="padding:28px">
    <p style="color:#333;margin-top:0">
      A(s) seguinte(s) máquina(s) está(ão)
      <strong>sem atividade há mais de 30 minutos</strong>:
    </p>
    <ul style="color:#333;line-height:1.9;padding-left:20px">
      {lista_html}
    </ul>

    <div style="background:#fff3e0;border-left:5px solid #e65100;
                padding:14px 18px;border-radius:8px;margin-top:20px;color:#555">
      O processo <em>worker</em> pode ter falhado ou a máquina pode estar
      offline. Verifique o estado do serviço nessas máquinas.
    </div>

    <p style="color:#999;font-size:12px;margin-top:24px;margin-bottom:0">
      Data: {agora}
    </p>
  </div>

  <div style="background:#333;color:#fff;text-align:center;
              padding:14px;font-size:12px">
    Este é um e-mail enviado automaticamente. Por favor, não responda.
  </div>
</div>
</body>
</html>"""

    nomes = ", ".join(maquinas)
    try:
        enviar_email(
            para=_ALERTA_EMAIL_TO,
            assunto=f"VX360 - Alerta: Máquina(s) Parada(s) | {nomes} | {agora}",
            html=html,
        )
    except Exception:
        logger.exception("Falha ao enviar alerta de máquinas paradas: %s", maquinas)
