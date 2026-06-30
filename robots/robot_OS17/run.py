from robots.robot_OS17.src.database.buscar_pedidos import buscar_pedidos_OS17
from robots.robot_OS17.src.database.credito_presumido_repository import (
    marcar_concluido,
    marcar_em_processamento,
    marcar_erro,
)
from robots.robot_OS17.src.database.popula_banco import carregar_pendentes_iniciais
from robots.robot_OS17.src.viasoft.erros.email_sender import notificar_erro_pedido
from robots.robot_OS17.src.viasoft.erros.error_handler import tratar_erro_pedido
from robots.robot_OS17.src.viasoft.regras_notaconf.router import filtro_notaconf
from robots.robot_OS17.src.viasoft.viasoft_fluxo_inicial import executar_fluxo_inicial_agro
from robots.robot_OS17.src.viasoft.viasoft_login import login_viasoft
from robots.robot_OS17.src.viasoft.viasoft_selecionar_estab import alterar_estabelecimento_trabalho


def run():
    print("[OS17] Carregando candidatos ao crédito presumido...")
    total = carregar_pendentes_iniciais()
    print(f"[OS17] {total} novos registros inseridos.")

    pedidos = buscar_pedidos_OS17()
    print(f"[OS17] {len(pedidos)} pedidos pendentes encontrados.")

    if not pedidos:
        print("[OS17] Nenhum pedido pendente. Encerrando.")
        return

    login_viasoft()

    estab_atual = None

    for pedido in pedidos:
        estab = str(pedido.get("estab", "")).strip()

        try:
            if estab != estab_atual:
                alterar_estabelecimento_trabalho(estab)
                estab_atual = estab

            executar_fluxo_inicial_agro()
            marcar_em_processamento(pedido)

            resultado = filtro_notaconf(pedido)

            marcar_concluido(pedido, resultado["nota"], resultado["seqnota"])
            print(
                f"[OS17] Pedido {pedido.get('numerocm')} concluído: "
                f"nota={resultado['nota']}, seqnota={resultado['seqnota']}"
            )

        except Exception as erro:
            screenshot_path = tratar_erro_pedido(pedido, erro, etapa="processamento")
            marcar_erro(pedido)
            notificar_erro_pedido(
                pedido,
                motivo=str(erro),
                screenshot_path=screenshot_path,
            )

    print("[OS17] Processamento finalizado.")


if __name__ == "__main__":
    run()
