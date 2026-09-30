from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetencaoImposto:
    nome: str
    retido: bool
    motivo: str
    alerta: str | None = None


def _to_float(valor: str | None) -> float:
    texto = str(valor or "").strip()

    if not texto:
        return 0.0

    texto = texto.replace("R$", "").replace(" ", "")

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return 0.0


def analisar_retencoes(
    dados: dict[str, str],
) -> dict[str, RetencaoImposto]:

    resultado: dict[str, RetencaoImposto] = {}

    retpis = dados.get("RETPISCOFINS", "")
    retiss = dados.get("RETISSQN", "")

    valor_retencao = _to_float(dados.get("VALOR_RETENCAO"))

    valores = {
        "PIS": _to_float(dados.get("VALOR_PIS")),
        "COFINS": _to_float(dados.get("VALOR_COFINS")),
        "CSLL": _to_float(dados.get("VALOR_CSLL")),
        "ISS": _to_float(dados.get("VALOR_ISSQN")),
        "INSS": _to_float(dados.get("VALOR_INSS")),
        "IRRF": _to_float(dados.get("VALOR_IRRF")),
    }

    # ==================================================
    # PIS
    # ==================================================

    resultado["PIS"] = RetencaoImposto(
        nome="PIS",
        retido=retpis in {"1", "3", "4", "5", "9"},
        motivo=f"RETPISCOFINS={retpis}",
    )

    # ==================================================
    # COFINS
    # ==================================================

    resultado["COFINS"] = RetencaoImposto(
        nome="COFINS",
        retido=retpis in {"1", "3", "4", "6", "7"},
        motivo=f"RETPISCOFINS={retpis}",
    )

    # ==================================================
    # CSLL
    # ==================================================

    resultado["CSLL"] = RetencaoImposto(
        nome="CSLL",
        retido=retpis in {"1", "3", "7", "8", "9"},
        motivo=f"RETPISCOFINS={retpis}",
    )

    # ==================================================
    # ISS
    # ==================================================

    iss_retido_codigo = retiss in {"2", "3"}

    iss_retido_financeiro = valor_retencao > 0 and round(valor_retencao, 2) == round(
        valores["ISS"], 2
    )

    if iss_retido_codigo:

        resultado["ISS"] = RetencaoImposto(
            nome="ISS",
            retido=True,
            motivo=f"RETISSQN={retiss}",
        )

    elif iss_retido_financeiro:

        resultado["ISS"] = RetencaoImposto(
            nome="ISS",
            retido=True,
            motivo=("VALOR_ISSQN fecha exatamente " "com VALOR_RETENCAO"),
            alerta=(f"RETISSQN={retiss} indica " "não retenção."),
        )

    else:

        resultado["ISS"] = RetencaoImposto(
            nome="ISS",
            retido=False,
            motivo=f"RETISSQN={retiss}",
        )

    # ==================================================
    # INSS
    # ==================================================

    resultado["INSS"] = RetencaoImposto(
        nome="INSS",
        retido=valores["INSS"] > 0,
        motivo="VALOR_INSS",
    )

    # ==================================================
    # IRRF
    # ==================================================

    resultado["IRRF"] = RetencaoImposto(
        nome="IRRF",
        retido=valores["IRRF"] > 0,
        motivo="VALOR_IRRF",
    )

    # ==================================================
    # LOG DE CONFERÊNCIA
    # ==================================================

    total_calculado = sum(
        valores[nome] for nome, decisao in resultado.items() if decisao.retido
    )

    diferenca = round(
        valor_retencao - total_calculado,
        2,
    )

    print(
        "[OS10] Conferência retenção | "
        f"Esperado={valor_retencao:.2f} "
        f"Calculado={total_calculado:.2f} "
        f"Diferença={diferenca:.2f}"
    )

    for nome, decisao in resultado.items():

        print(
            f"[OS10] {nome}: " f"RETIDO={decisao.retido} | " f"MOTIVO={decisao.motivo}"
        )

        if decisao.alerta:
            print(f"[OS10] ALERTA {nome}: " f"{decisao.alerta}")

    return resultado
