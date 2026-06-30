import traceback
from datetime import datetime
from pathlib import Path

from robots.robot_OS14.src.database.buscar_pedidos import buscar_pedidos_OS14
from robots.robot_OS14.src.viasoft.erros.email_sender import notificar_erro_pedido
from robots.robot_OS14.src.viasoft.regras_notaconf.router import filtro_notaconf
from robots.robot_OS14.src.viasoft.viasoft_fluxo_inicial import executar_fluxo_inicial_agro
from robots.robot_OS14.src.viasoft.viasoft_login import login_viasoft
from robots.robot_OS14.src.viasoft.viasoft_selecionar_estab import alterar_estabelecimento_trabalho


LOG_DIR = Path("logs")
LOG_ERROS = LOG_DIR / "pedidos_com_erro_OS14.txt"
LOG_IGNORADOS = LOG_DIR / "pedidos_ignorados_OS14.txt"

LIMITE_ERROS_CONSECUTIVOS = 10


def obter_valor(pedido: dict, chave: str) -> str:
    return str(pedido.get(chave, "")).strip()


def montar_chave_pedido(pedido: dict) -> str:
    estab = obter_valor(pedido, "estab")
    num_ped = obter_valor(pedido, "num_ped")
    fornecedor = obter_valor(pedido, "fornecedor")
    return f"{estab}|{num_ped}|{fornecedor}"


def carregar_pedidos_ignorados() -> set[str]:
    if not LOG_IGNORADOS.exists():
        return set()

    with LOG_IGNORADOS.open("r", encoding="utf-8") as arquivo:
        return {linha.strip() for linha in arquivo if linha.strip()}


def registrar_pedido_ignorado(pedido: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    chave_pedido = montar_chave_pedido(pedido)

    with LOG_IGNORADOS.open("a", encoding="utf-8") as arquivo:
        arquivo.write(f"{chave_pedido}\n")


def registrar_erro_pedido(pedido: dict, erro: Exception) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with LOG_ERROS.open("a", encoding="utf-8") as arquivo:
        arquivo.write("=" * 80 + "\n")
        arquivo.write(f"Data/Hora : {data_hora}\n")
        arquivo.write(f"ESTAB     : {obter_valor(pedido, 'estab')}\n")
        arquivo.write(f"NUM_PED   : {obter_valor(pedido, 'num_ped')}\n")
        arquivo.write(f"Fornecedor: {obter_valor(pedido, 'fornecedor')}\n")
        arquivo.write(f"Regra     : {obter_valor(pedido, 'regra_notaconf')}\n")
        arquivo.write(f"Erro      : {erro}\n")
        arquivo.write("\nTraceback:\n")
        arquivo.write(traceback.format_exc())
        arquivo.write("\n")


def run() -> None:
    pedidos = buscar_pedidos_OS14()

    if not pedidos:
        print("[OS14] Nenhum pedido encontrado.")
        return

    pedidos_ignorados = carregar_pedidos_ignorados()

    login_viasoft()

    estab_atual = None
    pedidos_processados = set()
    erros_consecutivos = 0
    reiniciar_viasoft = False

    for pedido in pedidos:
        chave_pedido = montar_chave_pedido(pedido)

        if chave_pedido in pedidos_ignorados:
            print(f"[OS14] Pedido já registrado com erro. Ignorando: {chave_pedido}")
            continue

        if chave_pedido in pedidos_processados:
            print(f"[OS14] Pedido repetido na consulta. Ignorando: {chave_pedido}")
            continue

        pedidos_processados.add(chave_pedido)

        try:
            if reiniciar_viasoft:
                print("[OS14] Reiniciando Viasoft após erro anterior...")
                login_viasoft()
                estab_atual = None
                reiniciar_viasoft = False

            estab_pedido = str(pedido["estab"])

            print("=" * 40)
            print(f"[OS14] Processando ESTAB: {pedido.get('estab')}")
            print(f"[OS14] Processando NUM_PED: {pedido.get('num_ped')}")
            print(f"[OS14] Fornecedor: {pedido.get('fornecedor')}")
            print(f"[OS14] Regra_NotaConf: {pedido.get('regra_notaconf')}")
            print("=" * 40)

            if estab_pedido != estab_atual:
                alterar_estabelecimento_trabalho(estab_pedido)
                estab_atual = estab_pedido

            print("[OS14] Executando o fluxo inicial agro")
            executar_fluxo_inicial_agro()

            print("[OS14] Executando o filtro nota conf")
            filtro_notaconf(pedido)

            print("[OS14] Nota processada com sucesso")
            erros_consecutivos = 0

        except Exception as erro:
            erros_consecutivos += 1

            print("=" * 40)
            print("[OS14] Pedido falhou.")
            print(f"[OS14] Pedido: {chave_pedido}")
            print(f"[OS14] Erro: {erro}")
            print(f"[OS14] Erros consecutivos: {erros_consecutivos}/{LIMITE_ERROS_CONSECUTIVOS}")
            print("=" * 40)

            registrar_erro_pedido(pedido, erro)

            notificar_erro_pedido(
                pedido=pedido,
                motivo=str(erro),
                tirar_screenshot=True,
            )

            registrar_pedido_ignorado(pedido)
            pedidos_ignorados.add(chave_pedido)

            reiniciar_viasoft = True
            estab_atual = None

            if erros_consecutivos >= LIMITE_ERROS_CONSECUTIVOS:
                print("[OS14] Limite de erros consecutivos atingido. Encerrando.")
                break


if __name__ == "__main__":
    run()
