import oracledb

from config import CLIENT_PATH, DSN_DB, SENHA_DB, USUARIO_DB


if CLIENT_PATH:
    oracledb.init_oracle_client(lib_dir=CLIENT_PATH)


def get_connection():
    return oracledb.connect(
        user=USUARIO_DB,
        password=SENHA_DB,
        dsn=DSN_DB,
    )
