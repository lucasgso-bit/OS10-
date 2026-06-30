from robots.robot_OS17.src.viasoft.regras_notaconf.regra_616.fluxo import executar_regra_616


def filtro_notaconf(pedido: dict) -> dict:
    """Route the pedido to its notaconf rule and return the result."""
    return executar_regra_616(pedido)
