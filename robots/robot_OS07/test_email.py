"""Run this directly to test email sending: python test_email.py"""

import smtplib
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "ORS-SAFETICA.OUROSAFRA.LOCAL"
SMTP_PORT = 25
EMAIL_FROM = "matheus.correa@ourosafra.com.br"
EMAIL_TO = "matheus.correa@ourosafra.com.br"
EMAIL_PASSWORD = "Aes25869@@"


def _send_msg(server: smtplib.SMTP) -> None:
    msg = MIMEMultipart()
    msg["Subject"] = "VX360 - Teste de envio de email"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(
        MIMEText(
            "<h2>Teste OK</h2><p>Email de teste do notifier VX360.</p>",
            "html",
            "utf-8",
        )
    )
    server.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())
    print("    OK — email enviado!")


def test_smtp_connection() -> None:
    print(f"[1] Conectando ao SMTP: {SMTP_HOST}:{SMTP_PORT} ...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        print("    OK — conectado.")

        print("[2] EHLO ...")
        code, features = server.ehlo()
        print(f"    {code} — capacidades: {features.decode(errors='replace')}")

        # Tenta login; servidores internos às vezes aceitam sem TLS
        print(f"[3] Login como {EMAIL_FROM} ...")
        try:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            print("    OK — autenticado.")
        except smtplib.SMTPNotSupportedError:
            print("    Servidor não exige autenticação, seguindo sem login.")
        except smtplib.SMTPAuthenticationError as exc:
            print(f"    Falha de autenticação: {exc} — tentando sem login.")

        print(f"[4] Enviando email para {EMAIL_TO} ...")
        _send_msg(server)


def test_notify_error() -> None:
    print("\n[6] Testando notify_error completo (screenshot + email + delete) ...")
    from robots.robot_OS07.src.notifier import notify_error

    nota_fake = {
        "U_FISCAL_IO_CONT_ID": 9999,
        "NOTACONF": "255",
        "ESTAB": "1",
        "PLACA": "ABC1234",
        "ORDEMCARGA": "OC-TESTE",
        "NUMERONOTA": "000001",
        "CHAVEACESSO": "00000000000000000000000000000000000000000000",
        "NUMEROCM": "CM-TEST",
        "QUANTIDADE": "1000",
        "IEEMITENTE": "IE-TEST",
        "PRODUTOR": "PRODUTOR TESTE",
        "CLASSIF_LOCAL": "CL-TEST",
    }

    notify_error(nota_fake, "Teste manual — verificar se email chegou")
    print("    notify_error executado. Verifique a caixa de entrada.")


if __name__ == "__main__":
    try:
        test_smtp_connection()
    except Exception:
        print("\n=== ERRO no teste SMTP ===")
        traceback.print_exc()
        sys.exit(1)

    try:
        test_notify_error()
    except Exception:
        print("\n=== ERRO no notify_error ===")
        traceback.print_exc()
        sys.exit(1)
