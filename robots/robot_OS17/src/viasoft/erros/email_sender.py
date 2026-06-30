import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pyautogui

from config import EMAIL_FROM, EMAIL_PASSWORD, OS17_EMAIL_TO, SMTP_HOST, SMTP_PORT


def tirar_screenshot_base64() -> str | None:
    """Take a screenshot and return its file path."""
    try:
        path = "screenshot_erro_OS17.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        return path
    except Exception:
        return None


def notificar_erro_pedido(
    pedido: dict,
    motivo: str,
    screenshot_path: str | None = None,
    tirar_screenshot: bool = False,
) -> None:
    """Send an error notification email for a failed pedido."""
    if tirar_screenshot and screenshot_path is None:
        screenshot_path = tirar_screenshot_base64()

    destinatarios = [e.strip() for e in OS17_EMAIL_TO.split(",") if e.strip()]
    if not destinatarios:
        return

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = f"[OS17] Erro no pedido {pedido.get('numerocm', '?')} - ESTAB {pedido.get('estab', '?')}"

    corpo = f"""
    <html><body>
    <h3>Erro ao processar pedido OS17</h3>
    <ul>
        <li><b>ESTAB:</b> {pedido.get('estab', '?')}</li>
        <li><b>NumeroCM:</b> {pedido.get('numerocm', '?')}</li>
        <li><b>IE:</b> {pedido.get('ins_estad', '?')}</li>
        <li><b>Ano/Mês:</b> {pedido.get('ano', '?')}/{pedido.get('mes', '?')}</li>
        <li><b>Motivo:</b> {motivo}</li>
    </ul>
    </body></html>
    """
    msg.attach(MIMEText(corpo, "html"))

    if screenshot_path:
        try:
            with open(screenshot_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename=screenshot_erro.png",
            )
            msg.attach(part)
        except Exception:
            pass

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if EMAIL_PASSWORD:
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, destinatarios, msg.as_string())
    except Exception as e:
        print(f"[OS17] Falha ao enviar e-mail de erro: {e}")
