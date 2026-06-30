import time

from robots.robot_OS14.src.viasoft.erros.error_handler import tratar_erro_pedido
from robots.robot_OS14.src.viasoft.regras_notaconf.regra_799.preencher_conta_movimento import preencher_conta_movimento
from robots.robot_OS14.src.viasoft.regras_notaconf.regra_799.preencher_pessoa import preencher_pessoa
from robots.robot_OS14.src.viasoft.regras_notaconf.regra_799.preencher_regra_notaconf import preencher_regra_notaconf
from robots.robot_OS14.src.viasoft.regras_notaconf.utils.buscar_valor_acerto import buscar_valor_acerto
from robots.robot_OS14.src.viasoft.regras_notaconf.utils.clicar_apartirde import clicar_apartirde
from robots.robot_OS14.src.viasoft.regras_notaconf.utils.data_clicar_borracha import clicar_botao_nota_fiscal
from robots.robot_OS14.src.viasoft.regras_notaconf.utils.finalizar_salvar import finalizar_fluxo


def executar_regra_799(pedido: dict) -> None:
    try:
        print("Entrei na regra 799")

        preencher_regra_notaconf(pedido)
        time.sleep(1)

        preencher_pessoa(pedido)
        time.sleep(1)

        clicar_botao_nota_fiscal(pedido)
        time.sleep(1)

        clicar_apartirde(pedido)
        time.sleep(1)

        buscar_valor_acerto(pedido)
        time.sleep(1)

        preencher_conta_movimento(pedido)
        time.sleep(1)

        finalizar_fluxo(pedido)

    except Exception as erro:
        tratar_erro_pedido(pedido=pedido, erro=erro, etapa="regra_799")
        raise
