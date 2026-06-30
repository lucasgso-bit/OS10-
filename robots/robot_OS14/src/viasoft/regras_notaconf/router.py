from robots.robot_OS14.src.viasoft.regras_notaconf.regra_27.fluxo import executar_regra_27
from robots.robot_OS14.src.viasoft.regras_notaconf.regra_799.fluxo import executar_regra_799
from robots.robot_OS14.src.viasoft.regras_notaconf.regra_800.fluxo import executar_regra_800


def filtro_notaconf(pedido: dict) -> None:
    regra = str(pedido["regra_notaconf"])

    print(f"REGRA_NOTACONF recebida: {regra}")

    if regra == "800" or regra == "825":
        executar_regra_800(pedido)

    elif regra in ("27", "502", "37", "44"):
        executar_regra_27(pedido)

    elif regra == "799":
        executar_regra_799(pedido)

    else:
        raise ValueError(f"Regra NOTACONF não mapeada: {regra}")
