"""Configure environment variables for the WNota 255 robot.

Load database, robot, and Agro application settings from the environment.

Developed by: Matheus correa
Updated by: Matheus correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from pathlib import Path
import socket
import sys
import socket
import getpass

from dotenv import load_dotenv
import os

# Quando empacotado pelo PyInstaller, usa o diretório do .exe como base.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
LOG_DIR = BASE_DIR / "logs"

USUARIO_DB = os.getenv("USUARIO_DB", "")
SENHA_DB = os.getenv("SENHA_DB", "")
DSN_DB = os.getenv("DSN_DB", "")
CLIENT_PATH = os.getenv("CLIENT_PATH", "")

AGRO_EXE = os.getenv("AGRO_EXE", r"C:\Viasoft\Client\Agro\agro3c.exe")
FINAGRO_EXE = os.getenv("FINAGRO_EXE", r"C:\Viasoft\Client\Agro\FinAgro3C.exe")
COMPUTADOR_ROBO: str = os.getenv("COMPUTADOR_ROBO") or getpass.getuser()
AGRO_USUARIO = os.getenv("AGRO_USUARIO", "RPA.OS07")
AGRO_SENHA = os.getenv("AGRO_SENHA", "")
OS18_SMTP_TO = os.getenv("OS18_SMTP_TO", "joao.netto@ourosafra.com.br")

SMTP_HOST = os.getenv("SMTP_HOST", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

TICKETLOG_BASE_URL: str = os.getenv("TICKETLOG_BASE_URL", "")
TICKETLOG_AUTHORIZATION: str = os.getenv("TICKETLOG_AUTHORIZATION", "")
TICKETLOG_CODIGO_CLIENTE: int = int(os.getenv("TICKETLOG_CODIGO_CLIENTE", "0"))
TICKETLOG_EMAIL_TO: str = os.getenv("TICKETLOG_EMAIL_TO", "")
