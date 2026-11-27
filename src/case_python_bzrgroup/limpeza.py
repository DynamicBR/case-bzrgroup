from pathlib import Path
import pandas as pd

PASTA_ENTRADA = Path("dados_implementacao")
HUB = "hub_implementacao.csv"
TRIBUNAL = "tribunal_implementacao.csv"
APRESENTACOES = "apresentacoes_implementacao.json"
PAGAMENTOS = "pagamentos_implementacao.json"


def limpar_processo(serie: pd.Series) -> pd.Series:
    """Mantém apenas os dígitos numéricos de uma coluna de processos."""
    return serie.fillna("").astype(str).str.replace(r"\D", "", regex=True)


def formatar_cnj(digitos: str) -> str:
    """Formata os 20 dígitos no padrão CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO)."""
    limpo = "".join(ch for ch in str(digitos or "") if ch.isdigit())
    if len(limpo) == 20:
        return f"{limpo[:7]}-{limpo[7:9]}.{limpo[9:13]}.{limpo[13]}.{limpo[14:16]}.{limpo[16:20]}"
    return limpo


def converter_valor_serie(serie: pd.Series) -> pd.Series:
    """Converte coluna mista (float 15000.0, texto BR '2.500,50' e None) para float."""
    return pd.to_numeric(
        serie.astype(str)
        .str.replace(r"\.(?=\d{3})", "", regex=True)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def padronizar_data_pagamento(serie: pd.Series) -> pd.Series:
    """Padroniza datas 'AAAA-MM-DD' e 'DD/MM/AAAA' para 'AAAA-MM-DD'."""
    datas_iso = pd.to_datetime(serie, format="%Y-%m-%d", errors="coerce")
    datas_br = pd.to_datetime(serie, format="%d/%m/%Y", errors="coerce")
    return datas_iso.fillna(datas_br).dt.strftime("%Y-%m-%d")


def converter_data_brasilia(valor: str) -> pd.Timestamp:
    """Datas sem fuso já estão no dia civil de Brasília; datas com fuso são convertidas."""
    ts = pd.Timestamp(str(valor).strip())
    if ts.tzinfo is None:
        return ts.tz_localize("America/Sao_Paulo")
    return ts.tz_convert("America/Sao_Paulo")


def calcular_prazo_pagamento(serie_apresentado_em: pd.Series) -> pd.Series:
    """Aplica a regra constitucional de 2 de abril no fuso de Brasília."""
    datas_br = serie_apresentado_em.apply(converter_data_brasilia)
    ate_2_abril = (datas_br.dt.month < 4) | ((datas_br.dt.month == 4) & (datas_br.dt.day <= 2))
    ano_prazo = (datas_br.dt.year + 1).where(ate_2_abril, datas_br.dt.year + 2)
    return ano_prazo.astype(str) + "-12-31"


def executar_limpeza(
    pasta_entrada: Path = PASTA_ENTRADA,
    caminho_excel: Path = Path("base_final.xlsx"),
) -> dict[str, pd.DataFrame]:
    # Leitura dos arquivos
    df_hub = pd.read_csv(pasta_entrada / HUB)
    df_tribunal = pd.read_csv(pasta_entrada / TRIBUNAL, encoding="ISO-8859-1", sep=";")
    df_apresentacoes = pd.read_json(pasta_entrada / APRESENTACOES)
    df_pagamentos = pd.read_json(pasta_entrada / PAGAMENTOS)

    # Tratamento do df_tribunal
    df_tribunal["numero_processo"] = limpar_processo(df_tribunal["numero_processo"])
    df_tribunal.insert(2, "valor_a_pagar", converter_valor_serie(df_tribunal["valor_face"]))
    df_tribunal = df_tribunal.drop(columns=["valor_face"])

    # Tratamento do df_hub
    df_hub.insert(0, "numero_processo", limpar_processo(df_hub["processo"]))
    df_hub = df_hub.drop(columns=["processo"])
    df_hub.insert(2, "valor_a_pagar_hub", df_hub["valor_face"].astype(float))
    df_hub = df_hub.drop(columns=["valor_face"])
    df_hub["prazo_hub_original"] = df_hub["prazo_pagamento"]
    df_hub["prazo_pagamento"] = calcular_prazo_pagamento(df_hub["apresentado_em"])

    # Tratamento do df_apresentacoes
    df_apresentacoes.insert(0, "numero_processo", limpar_processo(df_apresentacoes["processo"]))
    df_apresentacoes = df_apresentacoes.drop(columns=["processo"])
    df_apresentacoes["prazo_pagamento"] = calcular_prazo_pagamento(df_apresentacoes["apresentado_em"])
    df_apresentacoes["apresentado_em"] = (
        df_apresentacoes["apresentado_em"].apply(converter_data_brasilia).dt.strftime("%Y-%m-%d")
    )

    # Tratamento do df_pagamentos
    df_pagamentos.insert(0, "numero_processo", limpar_processo(df_pagamentos["processo"]))
    df_pagamentos = df_pagamentos.drop(columns=["processo"])
    df_pagamentos.insert(2, "valor_evento", converter_valor_serie(df_pagamentos["valor"]))
    df_pagamentos = df_pagamentos.drop(columns=["valor"])
    df_pagamentos["data_pagamento"] = padronizar_data_pagamento(df_pagamentos["data_pagamento"])

    # Ordena por atualizado_em e mantém apenas a versão mais recente de cada evento_id
    df_pagamentos["atualizado_em_ts"] = pd.to_datetime(df_pagamentos["atualizado_em"], utc=True)
    df_pagamentos = df_pagamentos.sort_values(by="atualizado_em_ts")
    df_pagamentos = df_pagamentos.drop_duplicates(subset=["evento_id"], keep="last")

    # Separa eventos válidos dos eventos inválidos (quarentena)
    condicao_valida = (
        (df_pagamentos["numero_processo"].str.len() == 20)
        & df_pagamentos["valor_evento"].notna()
        & (df_pagamentos["valor_evento"] > 0)
        & df_pagamentos["data_pagamento"].notna()
        & df_pagamentos["tipo"].isin(["pagamento", "estorno"])
    )
    df_pagamentos_descartados = df_pagamentos[~condicao_valida].drop(columns=["atualizado_em_ts"]).copy()
    df_pagamentos_validos = df_pagamentos[condicao_valida].copy()

    df_pagamentos_descartados["motivo_descarte"] = "Registro inválido"
    df_pagamentos_descartados.loc[
        df_pagamentos_descartados["valor_evento"].isna(), "motivo_descarte"
    ] = "Valor nulo (null)"
    df_pagamentos_descartados.loc[
        df_pagamentos_descartados["valor_evento"] <= 0, "motivo_descarte"
    ] = "Valor menor ou igual a zero"
    df_pagamentos_descartados.loc[
        df_pagamentos_descartados["numero_processo"].str.len() != 20, "motivo_descarte"
    ] = "Número de processo vazio ou inválido"

    # No estorno o impacto líquido no total pago é negativo (-valor_evento)
    df_pagamentos_validos["valor_liquido"] = df_pagamentos_validos["valor_evento"].where(
        df_pagamentos_validos["tipo"] == "pagamento", -df_pagamentos_validos["valor_evento"]
    )

    # Criação da base de eventos válidos (LEFT JOIN + saldo acumulado) e resumo por precatório
    df_pagamentos_validos = df_pagamentos_validos.sort_values(
        by=["numero_processo", "data_pagamento", "atualizado_em_ts"]
    )
    df_base = (
        df_pagamentos_validos.merge(
            df_apresentacoes[["numero_processo", "apresentado_em", "prazo_pagamento"]],
            on="numero_processo",
            how="left",
        ).merge(
            df_tribunal[["numero_processo", "ente_devedor", "valor_a_pagar"]],
            on="numero_processo",
            how="left",
        )
    )
    df_base["total_pago_acumulado"] = df_base.groupby("numero_processo")["valor_liquido"].cumsum()
    df_base["valor_restante"] = df_base["valor_a_pagar"] - df_base["total_pago_acumulado"]

    # Resumo consolidado por precatório
    soma_por_processo = (
        df_pagamentos_validos.groupby("numero_processo", as_index=False)["valor_liquido"]
        .sum()
        .rename(columns={"valor_liquido": "total_pago"})
    )
    df_precatorios = (
        df_apresentacoes.merge(df_tribunal, on="numero_processo", how="outer")
        .merge(
            df_hub[["numero_processo", "ente", "valor_a_pagar_hub", "prazo_hub_original"]],
            on="numero_processo",
            how="outer",
        )
        .merge(soma_por_processo, on="numero_processo", how="left")
    )
    df_precatorios["total_pago"] = df_precatorios["total_pago"].fillna(0.0)
    df_precatorios["ente_devedor"] = df_precatorios["ente_devedor"].fillna(df_precatorios["ente"])
    df_precatorios["valor_a_pagar"] = df_precatorios["valor_a_pagar"].fillna(
        df_precatorios["valor_a_pagar_hub"]
    )
    df_precatorios["valor_restante"] = df_precatorios["valor_a_pagar"] - df_precatorios["total_pago"]

    # Formata CNJ para evitar notação científica no Excel
    df_base["numero_processo"] = df_base["numero_processo"].apply(formatar_cnj)
    df_pagamentos_descartados["numero_processo"] = df_pagamentos_descartados[
        "numero_processo"
    ].apply(formatar_cnj)
    df_precatorios["numero_processo"] = df_precatorios["numero_processo"].apply(formatar_cnj)

    colunas_base = [
        "numero_processo",
        "evento_id",
        "ente_devedor",
        "tipo",
        "valor_a_pagar",
        "valor_evento",
        "valor_liquido",
        "total_pago_acumulado",
        "valor_restante",
        "apresentado_em",
        "prazo_pagamento",
        "data_pagamento",
        "atualizado_em",
    ]
    df_base = df_base[colunas_base]

    with pd.ExcelWriter(caminho_excel) as writer:
        df_base.to_excel(writer, sheet_name="pagamentos_validos", index=False)
        df_precatorios.to_excel(writer, sheet_name="precatorios_consolidados", index=False)
        df_pagamentos_descartados.to_excel(writer, sheet_name="eventos_descartados", index=False)

    return {
        "precatorios": df_precatorios,
        "pagamentos_validos": df_base,
        "eventos_descartados": df_pagamentos_descartados,
    }


if __name__ == "__main__":
    executar_limpeza()
