from robots.robot_OS17.src.viasoft.regras_notaconf.regra_616.impressao_da_nota import finalizar_parte_2
from robots.robot_OS17.src.viasoft.regras_notaconf.regra_616.preencher_item_cfop import preencher_item_cfop_valorimposto
from robots.robot_OS17.src.viasoft.regras_notaconf.regra_616.preencher_pessoa import preencher_pessoa
from robots.robot_OS17.src.viasoft.regras_notaconf.regra_616.preencher_regra_notaconf import preencher_regra_notaconf
from robots.robot_OS17.src.viasoft.regras_notaconf.regra_616.salvar_parte_1 import finalizar_parte_1


def executar_regra_616(pedido: dict) -> dict:
    """Execute the full notaconf 616 flow and return {'nota': ..., 'seqnota': ...}."""
    preencher_regra_notaconf()
    preencher_pessoa(pedido)
    preencher_item_cfop_valorimposto(pedido)
    finalizar_parte_1()
    resultado = finalizar_parte_2()
    return resultado
