"""Configure environment variables for the WNota 255 robot.

Load database, robot, and Agro application settings from the environment.

Developed by: Matheus correa
Updated by: Matheus correa
Last Modified: 2026-05-15
Version: 1.0.0
"""

from pathlib import Path
import sys

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